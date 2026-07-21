import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")

# Tekshirish oralig'i (sekundlarda)
# 3847 region bor — har bir sikl taxminan 30-60 daqiqa oladi
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))

# SQLite database
DB_PATH = os.getenv("DB_PATH", "seen_posts.db")

# Bir vaqtda nechta region parallel tekshirilsin
CONCURRENT_REGIONS = int(os.getenv("CONCURRENT_REGIONS", "10"))

# Har bir so'rov orasidagi kutish (sekundlarda) — ban bo'lmaslik uchun
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "0.3"))
