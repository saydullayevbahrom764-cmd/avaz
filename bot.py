# ============================================================
#  BOT ASOSIY MANTIQ
#  10 BUY + 10 SELL ochish → $2 foydada yopish → takrorlash
# ============================================================

import time
import logging
from oanda_trader import OandaTrader
from config import (
    BUY_COUNT, SELL_COUNT, PROFIT_TARGET_USD,
    CHECK_INTERVAL, MAX_SPREAD_PIPS, INSTRUMENT
)

logger = logging.getLogger(__name__)

# ============================================================
#  YORDAMCHI FUNKSIYALAR
# ============================================================

def print_banner():
    print("=" * 55)
    print("   🤖 XAUUSD AVTOMATIK SAVDO BOTI")
    print("   10 BUY + 10 SELL | Maqsad: $2 foyda")
    print("=" * 55)


def check_spread(trader: OandaTrader) -> bool:
    """Spread chegaradan kichik bo'lsa True qaytaradi"""
    price = trader.get_price()
    if not price:
        return False
    spread_pips = price["spread"] * 10  # XAUUSD uchun 1 pip = 0.1
    if spread_pips > MAX_SPREAD_PIPS:
        logger.warning(f"⚠️  Spread juda katta: {spread_pips:.2f} pips (max: {MAX_SPREAD_PIPS})")
        return False
    logger.info(f"Spread: {spread_pips:.2f} pips ✅")
    return True


# ============================================================
#  BOSQICH 1: 10 BUY + 10 SELL OCHISH
# ============================================================

def open_all_positions(trader: OandaTrader) -> list:
    """10 ta BUY va 10 ta SELL pozitsiya ochish"""

    logger.info("=" * 50)
    logger.info(f"🚀 Yangi sikl boshlandi!")
    logger.info(f"   {BUY_COUNT} BUY + {SELL_COUNT} SELL ochamiz...")
    logger.info("=" * 50)

    opened_trades = []

    # --- 10 ta BUY ---
    logger.info(f"📈 BUY pozitsiyalar ochilmoqda ({BUY_COUNT} ta)...")
    for i in range(1, BUY_COUNT + 1):
        label = f"buy_{i}"
        trade = trader.open_order("buy", label=label)
        if trade:
            opened_trades.append(trade)
            logger.info(f"  [{i}/{BUY_COUNT}] BUY ochildi | ID: {trade['trade_id']} | Narx: {trade['price']}")
        else:
            logger.error(f"  [{i}/{BUY_COUNT}] BUY ochishda XATO!")
        time.sleep(0.3)  # APIni haddan tashqari yuklamaslik uchun

    # --- 10 ta SELL ---
    logger.info(f"📉 SELL pozitsiyalar ochilmoqda ({SELL_COUNT} ta)...")
    for i in range(1, SELL_COUNT + 1):
        label = f"sell_{i}"
        trade = trader.open_order("sell", label=label)
        if trade:
            opened_trades.append(trade)
            logger.info(f"  [{i}/{SELL_COUNT}] SELL ochildi | ID: {trade['trade_id']} | Narx: {trade['price']}")
        else:
            logger.error(f"  [{i}/{SELL_COUNT}] SELL ochishda XATO!")
        time.sleep(0.3)

    logger.info(f"✅ Jami {len(opened_trades)}/{BUY_COUNT + SELL_COUNT} pozitsiya ochildi")
    return opened_trades


# ============================================================
#  BOSQICH 2: $2 FOYDANI KUTISH VA YOPISH
# ============================================================

def wait_for_profit_and_close(trader: OandaTrader) -> float:
    """
    Har CHECK_INTERVAL soniyada foyda tekshiriladi.
    Jami foyda >= $2 bo'lsa, barcha pozitsiyalar yopiladi.
    """
    logger.info(f"⏳ Foyda kuzatuvi boshlandi | Maqsad: ${PROFIT_TARGET_USD}")
    logger.info(f"   Tekshirish oralig'i: {CHECK_INTERVAL} soniya")

    cycle = 0
    while True:
        cycle += 1
        time.sleep(CHECK_INTERVAL)

        # Ochiq pozitsiyalar bormi?
        counts = trader.count_open_trades()
        if counts["total"] == 0:
            logger.warning("⚠️  Ochiq pozitsiyalar yo'q! Yangi sikl boshlanadi...")
            return 0.0

        # Jami foyda hisoblash
        total_pnl = trader.get_total_unrealized_pnl()

        # Status chiqarish
        logger.info(
            f"[Tekshiruv #{cycle}] "
            f"PnL: {total_pnl:+.4f} USD | "
            f"Maqsad: ${PROFIT_TARGET_USD} | "
            f"Pozitsiyalar: {counts['total']} (B:{counts['buy']} S:{counts['sell']})"
        )

        # Maqsadga yetdimi?
        if total_pnl >= PROFIT_TARGET_USD:
            logger.info(f"🎯 MAQSADGA YETILDI! Foyda: ${total_pnl:.4f}")
            logger.info("🔒 Barcha pozitsiyalar yopilmoqda...")
            closed = trader.close_all_trades()
            logger.info(f"✅ {closed} ta pozitsiya yopildi | Foyda: ~${total_pnl:.4f}")
            return total_pnl


# ============================================================
#  ASOSIY BOT SIKLI
# ============================================================

def run_bot():
    """Asosiy bot sikli: ochish → kutish → yopish → takrorlash"""

    print_banner()
    trader = OandaTrader()

    # Hisob ma'lumotlarini tekshirish
    account = trader.get_account_info()
    if not account:
        logger.error("❌ OANDA API ulanmadi! config.py dagi API KEY va ACCOUNT ID ni tekshiring.")
        return

    logger.info(f"💰 Hisob balansi: {account['balance']} USD")

    sikl_soni = 0
    jami_foyda = 0.0

    while True:
        sikl_soni += 1
        logger.info(f"\n{'='*55}")
        logger.info(f"  📊 SIKL #{sikl_soni} boshlandi")
        logger.info(f"  Jami to'plangan foyda: ${jami_foyda:.4f}")
        logger.info(f"{'='*55}")

        # 1) Spread tekshirish
        logger.info("🔍 Spread tekshirilmoqda...")
        spread_ok = False
        while not spread_ok:
            spread_ok = check_spread(trader)
            if not spread_ok:
                logger.info("⏳ Spread kichrayishini kutmoqda (10 soniya)...")
                time.sleep(10)

        # 2) Pozitsiyalarni ochish
        opened = open_all_positions(trader)
        if len(opened) < (BUY_COUNT + SELL_COUNT) * 0.5:
            logger.error("❌ Yetarli pozitsiya ochilmadi! 30 soniya kutib qayta uriniladi...")
            trader.close_all_trades()
            time.sleep(30)
            continue

        # 3) Foyda kutish va yopish
        sikl_foyda = wait_for_profit_and_close(trader)
        jami_foyda += sikl_foyda

        logger.info(f"🏁 Sikl #{sikl_soni} tugadi | Foyda: ${sikl_foyda:.4f} | Jami: ${jami_foyda:.4f}")

        # 4) Keyingi sikldan oldin 3 soniya pauza
        logger.info("⏸️  Keyingi siklga tayyorlanmoqda (3 soniya)...")
        time.sleep(3)


# ============================================================
#  DASTURNI ISHGA TUSHIRISH
# ============================================================

if __name__ == "__main__":
    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("\n🛑 Bot to'xtatildi (Ctrl+C)")
        logger.info("Barcha pozitsiyalarni yopish...")
        trader = OandaTrader()
        trader.close_all_trades()
        logger.info("✅ Tozalanish tugadi. Xayr!")
