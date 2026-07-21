# ============================================================
#  BOT ASOSIY MANTIQ
#  10 BUY + 10 SELL → $2 foydada yopish → takrorlash ♻️
# ============================================================

import time
import logging
from mt5_trader import MT5Trader
from config import BUY_COUNT, SELL_COUNT, PROFIT_TARGET, CHECK_INTERVAL

logger = logging.getLogger(__name__)


# ============================================================
#  BANNER
# ============================================================
def print_banner():
    print("=" * 55)
    print("   🤖 XAUUSD MT5 AVTOMATIK SAVDO BOTI")
    print(f"   {BUY_COUNT} BUY + {SELL_COUNT} SELL | Maqsad: ${PROFIT_TARGET}")
    print("=" * 55)


# ============================================================
#  BOSQICH 1: 10 BUY + 10 SELL OCHISH
# ============================================================
def open_all_positions(trader: MT5Trader) -> int:
    logger.info("=" * 50)
    logger.info(f"🚀 Yangi sikl | {BUY_COUNT} BUY + {SELL_COUNT} SELL ochamiz...")
    logger.info("=" * 50)

    count = 0

    # 10 ta BUY
    logger.info(f"📈 BUY pozitsiyalar ({BUY_COUNT} ta)...")
    for i in range(1, BUY_COUNT + 1):
        result = trader.open_order("buy")
        if result:
            count += 1
            logger.info(f"  [{i}/{BUY_COUNT}] BUY ✅ ticket:{result['ticket']} narx:{result['price']}")
        else:
            logger.error(f"  [{i}/{BUY_COUNT}] BUY ❌ xato!")
        time.sleep(0.3)

    # 10 ta SELL
    logger.info(f"📉 SELL pozitsiyalar ({SELL_COUNT} ta)...")
    for i in range(1, SELL_COUNT + 1):
        result = trader.open_order("sell")
        if result:
            count += 1
            logger.info(f"  [{i}/{SELL_COUNT}] SELL ✅ ticket:{result['ticket']} narx:{result['price']}")
        else:
            logger.error(f"  [{i}/{SELL_COUNT}] SELL ❌ xato!")
        time.sleep(0.3)

    logger.info(f"✅ Jami {count}/{BUY_COUNT + SELL_COUNT} pozitsiya ochildi")
    return count


# ============================================================
#  BOSQICH 2: $2 FOYDANI KUTISH VA YOPISH
# ============================================================
def wait_and_close(trader: MT5Trader) -> float:
    logger.info(f"⏳ Foyda kuzatuvi | Maqsad: ${PROFIT_TARGET} | Interval: {CHECK_INTERVAL}s")

    check = 0
    while True:
        time.sleep(CHECK_INTERVAL)
        check += 1

        counts = trader.count_positions()
        if counts["total"] == 0:
            logger.warning("⚠️  Ochiq pozitsiya yo'q! Yangi sikl boshlanadi...")
            return 0.0

        pnl = trader.get_total_profit()
        logger.info(
            f"[#{check}] PnL: {pnl:+.4f}$ | "
            f"Maqsad: ${PROFIT_TARGET} | "
            f"Pos: {counts['total']} (B:{counts['buy']} S:{counts['sell']})"
        )

        if pnl >= PROFIT_TARGET:
            logger.info(f"🎯 MAQSAD! Foyda: ${pnl:.4f} — barcha pozitsiyalar yopilmoqda...")
            closed = trader.close_all()
            logger.info(f"✅ {closed} ta pozitsiya yopildi | Foyda: ~${pnl:.4f}")
            return pnl


# ============================================================
#  ASOSIY SIKL
# ============================================================
def run_bot():
    print_banner()
    trader = MT5Trader()

    # MT5 ga ulanish
    if not trader.connect():
        logger.error("❌ MT5 ga ulanib bo'lmadi! config.py ni tekshiring.")
        return

    sikl    = 0
    jami_pnl = 0.0

    try:
        while True:
            sikl += 1
            logger.info(f"\n{'='*55}")
            logger.info(f"  📊 SIKL #{sikl} | Jami foyda: ${jami_pnl:.4f}")
            logger.info(f"{'='*55}")

            # 1) Pozitsiyalarni ochish
            opened = open_all_positions(trader)
            if opened < (BUY_COUNT + SELL_COUNT) // 2:
                logger.error("❌ Yetarli pozitsiya ochilmadi! 15s kutib qayta uriniladi...")
                trader.close_all()
                time.sleep(15)
                continue

            # 2) Foyda kutish va yopish
            profit = wait_and_close(trader)
            jami_pnl += profit

            logger.info(f"🏁 Sikl #{sikl} tugadi | Foyda: ${profit:.4f} | Jami: ${jami_pnl:.4f}")
            logger.info("⏸️  3 soniya pauza...")
            time.sleep(3)

    except KeyboardInterrupt:
        logger.info("\n🛑 Bot to'xtatildi (Ctrl+C)")
        logger.info("Barcha pozitsiyalar yopilmoqda...")
        trader.close_all()
        logger.info(f"✅ Tozalandi | Jami foyda: ${jami_pnl:.4f}")
    finally:
        trader.disconnect()


if __name__ == "__main__":
    run_bot()
