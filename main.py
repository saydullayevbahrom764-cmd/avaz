# ============================================================
#  MAIN.PY — BOTNI ISHGA TUSHIRISH
# ============================================================

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

from bot import run_bot

if __name__ == "__main__":
    run_bot()
