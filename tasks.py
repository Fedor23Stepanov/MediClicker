# tasks.py

import asyncio
import random
import uuid
from datetime import datetime
from urllib.parse import urlparse

from telegram.ext import CallbackContext
from sqlalchemy import select

from db import AsyncSessionLocal
from models import Queue, Event, DeviceOption, User, ProxyLog
from redirector import fetch_redirect, ProxyAcquireError

# Ограничивает одновременное выполнение fetch_redirect
semaphore = asyncio.Semaphore(1)

def shorten_url(full_url: str, max_len: int = 30) -> str:
    """
    Убирает протокол и сокращает URL до max_len символов:
    домен + … + хвост, всего не более max_len.
    """
    parsed = urlparse(full_url)
    rest = parsed.netloc + parsed.path + (f"?{parsed.query}" if parsed.query else "")
    if len(rest) <= max_len:
        return rest
    tail_len = max_len - len(parsed.netloc) - 1
    tail = rest[-tail_len:] if tail_len > 0 else rest[:max_len]
    return f"{parsed.netloc}…{tail}"

async def fetch_db_user(session, telegram_id: int):
    """Возвращает User по Telegram ID или None."""
    result = await session.execute(
        select(User).filter_by(user_id=telegram_id)
    )
    return result.scalar_one_or_none()

async def process_queue_item(item, bot):
    async with semaphore:
        async with AsyncSessionLocal() as session:
            # Выбираем случайное устройство
            result = await session.execute(select(DeviceOption.id))
            ids = result.scalars().all()
            chosen_id = random.choice(ids)
            device_obj = await session.get(DeviceOption, chosen_id)
            device = {
                "ua": device_obj.ua,
                "css_size": device_obj.css_size,
                "platform": device_obj.platform,
                "dpr": device_obj.dpr,
                "mobile": device_obj.mobile,
                "model": device_obj.model,
            }

            proxy_id = str(uuid.uuid4())
            initial_url = final_url = ip = isp = None
            attempts = []
            state = "redirector_error"

            try:
                (initial_url,
                 final_url,
                 ip,
                 isp,
                 _,
                 attempts) = await asyncio.to_thread(fetch_redirect, item.url, device)
                state = "success"
            except ProxyAcquireError as e:
                state = "proxy_error"
                attempts = e.attempts
                # гарантируем, что initial_url не None
                initial_url = item.url
            except Exception:
                state = "redirector_error"
                initial_url = item.url

            # Логируем proxy_attempts
            for a in attempts:
                session.add(ProxyLog(
                    id=proxy_id,
                    attempt=a["attempt"],
                    ip=a.get("ip"),
                    city=a.get("city"),
                ))

            # Сохраняем событие
            session.add(Event(
                user_id=item.user_id,
                device_option_id=(device_obj.id if state == "success" else None),
                state=state,
                proxy_id=proxy_id,
                initial_url=initial_url,
                final_url=final_url,
                ip=ip,
                isp=isp,
            ))

            # Помечаем задачу как выполненную
            db_item = await session.get(Queue, item.id)
            db_item.status = "done"

            # Фиксируем все изменения
            await session.commit()

            # Отправляем уведомление
            db_user = await fetch_db_user(session, item.user_id)
            if db_user:
                # при ошибках initial_url теперь всегда задана
                url_to_show = initial_url or item.url
                init_short = shorten_url(url_to_show)
                init_link  = f'<a href="{url_to_show}">{init_short}</a>'
                device_name = device_obj.model

                if state == "success":
                    final_short = shorten_url(final_url)
                    final_link  = f'<a href="{final_url}">{final_short}</a>'
                    text = (
                        "Успешный переход ✅\n"
                        f"▶️ {init_link}\n"
                        f"⏹️ {final_link}\n"
                        f"🌐 ip {ip or '—'}\n"
                        f"📱 {device_name}"
                    )
                else:
                    text = (
                        "Ошибка перехода ❌\n"
                        f"{init_link}"
                    )

                await bot.send_message(
                    chat_id=item.user_id,
                    text=text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_to_message_id=item.message_id
                )

async def tick(context: CallbackContext):
    bot = context.bot
    async with AsyncSessionLocal() as session:
        now = datetime.now()

        # В одной транзакции переводим pending → in_progress
        async with session.begin():
            result = await session.execute(
                select(Queue)
                .where(Queue.status == "pending", Queue.transition_time <= now)
            )
            items = result.scalars().all()

            for item in items:
                item.status = "in_progress"
        # session.begin() автоматически коммитит изменения

    # Запускаем обработку вне транзакции
    for item in items:
        asyncio.create_task(process_queue_item(item, bot))

def setup_scheduler(app):
    """
    Настраивает JobQueue PTB:
      - tick каждую минуту, первый запуск сразу.
    """
    app.job_queue.run_repeating(tick, interval=20, first=0)
