# ============================================================
#  MAIN.PY — BOTNI ISHGA TUSHIRISH
#  Ikki rejim:
#    python main.py        → To'g'ridan-to'g'ri bot (webhook yo'q)
#    python main.py server → Webhook server + bot birgalikda
# ============================================================

import sys
import logging
import threading

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_direct():
    """To'g'ridan-to'g'ri botni ishga tushirish (webhook yo'q)"""
    from bot import run_bot
    logger.info("▶️  Rejim: TO'G'RIDAN-TO'G'RI BOT")
    run_bot()


def run_server():
    """Webhook server + bot birgalikda"""
    from webhook import start_webhook_server
    logger.info("▶️  Rejim: WEBHOOK SERVER")
    logger.info("   Bot webhook orqali boshqariladi")
    logger.info("   POST http://localhost:5000/webhook")
    start_webhook_server()


if __name__ == "__main__":
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "direct"

    print("=" * 55)
    print("   🤖 XAUUSD SAVDO BOTI — main.py")
    print("=" * 55)

    if mode == "server":
        run_server()
    else:
        run_direct()
