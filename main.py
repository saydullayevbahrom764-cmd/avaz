# ============================================================
#  MAIN.PY — GRID BOT ISHGA TUSHIRISH
#  python main.py          → Grid bot
#  python main.py old      → Eski 10buy+10sell bot
# ============================================================

import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

if __name__ == "__main__":
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "grid"

    if mode == "old":
        # Eski bot (10 buy + 10 sell)
        from bot import run_bot
        print("▶️  Rejim: ESKI BOT (10 BUY + 10 SELL)")
        run_bot()
    else:
        # Yangi Grid bot
        from grid_bot import run_grid_bot
        print("▶️  Rejim: GRID BOT (6 BUY + 6 SELL, 20pt)")
        run_grid_bot()
