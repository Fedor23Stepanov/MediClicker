import logging
from telegram.ext import ApplicationBuilder
from config import TELEGRAM_TOKEN
from db import init_db
from handlers import register_handlers
from tasks import setup_scheduler

# Настраиваем логирование в консоль и файл
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("logs/bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

print(">>> MAIN.PY START")
logging.info("Бот запускается через main.py")

# Этот колбэк будет вызван внутри event loop ДО polling
async def on_startup(app):
    logging.info("on_startup() вызван")
    print(">>> on_startup() called")
    await init_db()
    logging.info("База данных инициализирована")
    print(">>> DB инициализирована")

def main():
    print(">>> main() called")
    logging.info("main() начат")

    if TELEGRAM_TOKEN is None:
        logging.error("TELEGRAM_TOKEN = None. Проверь .env и config.py")
        print("!!! TELEGRAM_TOKEN отсутствует !!!")
        return

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(on_startup)
        .build()
    )
    print(">>> app построен")
    logging.info("Приложение построено")

    register_handlers(app)
    print(">>> handlers зарегистрированы")
    logging.info("Handlers зарегистрированы")

    setup_scheduler(app)
    print(">>> scheduler настроен")
    logging.info("Scheduler настроен")

    print(">>> Запускаем polling...")
    logging.info("Polling запускается")
    app.run_polling()
    logging.info("Polling завершён")
    print(">>> polling завершён")

if __name__ == "__main__":
    main()
