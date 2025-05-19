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

logging.info("Бот запускается через main.py")

# Этот колбэк будет вызван внутри event loop ДО polling
async def on_startup(app):
    try:
        logging.info("on_startup() вызван")
        await init_db()
        logging.info("База данных инициализирована")
    except Exception:
        logging.exception("Error in on_startup")

def main():
    logging.info("main() начат")

    if TELEGRAM_TOKEN is None:
        logging.error("TELEGRAM_TOKEN = None. Проверь .env и config.py")
        return

    # Собираем приложение
    try:
        app = (
            ApplicationBuilder()
            .token(TELEGRAM_TOKEN)
            .post_init(on_startup)
            .build()
        )
        logging.info("Приложение построено")
    except Exception:
        logging.exception("Error building Application")
        return

    # Регистрируем хендлеры
    try:
        register_handlers(app)
        logging.info("Handlers зарегистрированы")
    except Exception:
        logging.exception("Error registering handlers")

    # Настраиваем планировщик
    try:
        setup_scheduler(app)
        logging.info("Scheduler настроен")
    except Exception:
        logging.exception("Error setting up scheduler")

    # Запускаем polling
    logging.info("Polling запускается")
    try:
        app.run_polling()
    except Exception:
        logging.exception("Error during polling")
    finally:
        logging.info("Polling завершён")

if __name__ == "__main__":
    main()
