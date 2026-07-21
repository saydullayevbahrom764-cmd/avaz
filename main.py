# ================================================================
#  MAIN.PY — BOTNI ISHGA TUSHIRISH
#
#  Ishlatish:
#    py main.py          → Professional Multi-TF bot
#    py main.py grid     → Grid bot (6buy+6sell)
#    py main.py old      → Eski bot (10buy+10sell)
# ================================================================

import sys
import logging
from logging.handlers import RotatingFileHandler


def setup_logging():
    """Log sozlash — fayl + konsol"""
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Fayl handler (max 5MB, 3 ta backup)
    file_handler = RotatingFileHandler(
        "bot.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # Konsol handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)


if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)

    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "pro"

    print("\n" + "=" * 62)
    print("   🤖 XAUUSD SAVDO BOTI")
    print("=" * 62)

    if mode == "grid":
        print("   Rejim: GRID BOT (6 BUY + 6 SELL, 20pt)\n")
        from grid_bot import run_grid_bot
        run_grid_bot()

    elif mode == "old":
        print("   Rejim: ESKI BOT (10 BUY + 10 SELL)\n")
        from bot import run_bot as old_run
        # Eski bot.py dan import
        old_run()

    else:
        print("   Rejim: PROFESSIONAL BOT (Multi-TF + 8 Indikator)\n")
        from bot import run_bot
        run_bot()
