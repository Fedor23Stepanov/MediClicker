#config.py

import os
from dotenv import load_dotenv

load_dotenv()

# ======================
# Telegram Bot Settings
# ======================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
INITIAL_ADMIN  = os.getenv("INITIAL_ADMIN")

# ======================
# Database Settings
# ======================
DATABASE_URL   = os.getenv("DATABASE_URL",   "sqlite+aiosqlite:///./app.db")

# ======================
# Proxy / IP-API Settings
# ======================
PROXY_USERNAME = os.getenv("PROXY_USERNAME")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")
PROXY_DNS      = os.getenv("PROXY_DNS")

IP_API_URL     = os.getenv("IP_API_URL",     "http://ip-api.com/json")

# ======================
# Timing & Retry Limits
# ======================
CHECK_INTERVAL     = int(os.getenv("CHECK_INTERVAL",     "1"))
REDIRECT_TIMEOUT   = int(os.getenv("REDIRECT_TIMEOUT",   "20"))
MAX_PROXY_ATTEMPTS = int(os.getenv("MAX_PROXY_ATTEMPTS", "10"))
