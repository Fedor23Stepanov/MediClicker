#db.py

import json
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func
from config import DATABASE_URL, INITIAL_ADMIN
from models import Base, User, DeviceOption

# Создаём асинхронный движок и сессию
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    """
    Инициализация БД:
    1) Создаёт таблицы по всем моделям.
    2) Загружает device_options из devices.json, если таблица пуста.
    3) Добавляет initial admin в users со статусом pending, если нет.
    """
    # 1) Создать таблицы
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        logging.error("init_db: не удалось создать таблицы: %s", e, exc_info=True)
        return

    # 2) Наполнить device_options и добавить админа
    async with AsyncSessionLocal() as session:
        try:
            # Проверяем, пуста ли таблица device_options
            count = await session.scalar(
                select(func.count()).select_from(DeviceOption)
            )
        except Exception as e:
            logging.error("init_db: ошибка при select count DeviceOption: %s", e, exc_info=True)
            return

        if count == 0:
            try:
                with open("devices.json", encoding="utf-8") as f:
                    data = json.load(f)
                for id_str, device in data.items():
                    session.add(DeviceOption(
                        id=int(id_str),
                        ua=device["ua"],
                        css_size=device["css_size"],
                        platform=device["platform"],
                        dpr=device["dpr"],
                        mobile=device["mobile"],
                        model=device.get("model")
                    ))
            except Exception as e:
                logging.error("init_db: не удалось загрузить devices.json: %s", e, exc_info=True)

        # Проверяем наличие initial admin по username
        try:
            result = await session.execute(
                select(User).filter_by(username=INITIAL_ADMIN)
            )
            admin = result.scalar_one_or_none()
            if not admin:
                session.add(User(
                    username=INITIAL_ADMIN,
                    role="admin",
                    status="pending",
                    invited_by=None
                ))
            await session.commit()
        except Exception as e:
            logging.error("init_db: ошибка при добавлении initial admin или коммите: %s", e, exc_info=True)
