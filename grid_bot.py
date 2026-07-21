# ============================================================
#  GRID TRADING BOT - ASOSIY MANTIQ
#  6 BUY + 6 SELL, 20 point grid, $5 foydada yopish
# ============================================================

import MetaTrader5 as mt5
import time
import logging
from config import (
    MT5_LOGIN, MT5_PASSWORD, MT5_SERVER,
    SYMBOL, LOT, MAGIC,
    GRID_STEP, BUY_COUNT, SELL_COUNT,
    PROFIT_TARGET, MAX_LOSS, CHECK_INTERVAL
)

# Logging sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("grid_bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================
#  MT5 ULANISH
# ============================================================

def connect() -> bool:
    if not mt5.initialize():
        logger.error(f"MT5 initialize xato: {mt5.last_error()}")
        return False
    ok = mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
    if not ok:
        logger.error(f"MT5 login xato: {mt5.last_error()}")
        mt5.shutdown()
        return False
    info = mt5.account_info()
    logger.info(f"✅ MT5 ulandi | Hisob: {info.login} | Balans: {info.balance:.2f}$ | Server: {info.server}")
    return True


def disconnect():
    mt5.shutdown()
    logger.info("MT5 ulanishi uzildi")


# ============================================================
#  NARX VA SYMBOL MA'LUMOTLARI
# ============================================================

def get_tick():
    """Joriy bid/ask narxini olish"""
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        logger.error(f"Tick olinmadi: {mt5.last_error()}")
        return None
    return tick


def get_point():
    """Symbol point qiymatini olish"""
    info = mt5.symbol_info(SYMBOL)
    if info is None:
        return 0.01
    return info.point


def ensure_symbol():
    """Symbol Market Watch da borligini tekshirish"""
    info = mt5.symbol_info(SYMBOL)
    if info is None or not info.visible:
        mt5.symbol_select(SYMBOL, True)
        time.sleep(0.5)


# ============================================================
#  BITTA BUYURTMA OCHISH
# ============================================================

def open_order(direction: str, price: float) -> dict | None:
    """
    direction: 'buy' yoki 'sell'
    price: ochilish narxi (limit emas, market narxiga yaqin)
    """
    tick = get_tick()
    if tick is None:
        return None

    if direction == "buy":
        order_type = mt5.ORDER_TYPE_BUY
        exec_price = tick.ask
    else:
        order_type = mt5.ORDER_TYPE_SELL
        exec_price = tick.bid

    request = {
        "action":       mt5.TRADE_ACTION_DEAL,
        "symbol":       SYMBOL,
        "volume":       LOT,
        "type":         order_type,
        "price":        exec_price,
        "deviation":    30,
        "magic":        MAGIC,
        "comment":      f"grid_{direction}_{price:.2f}",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)

    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        code = result.retcode if result else "None"
        logger.error(f"❌ {direction.upper()} xato | retcode: {code} | narx: {exec_price}")
        return None

    logger.info(f"✅ {direction.upper()} ochildi | ticket: {result.order} | narx: {exec_price:.5f}")
    return {"ticket": result.order, "direction": direction, "price": exec_price}


# ============================================================
#  GRID POZITSIYALARINI OCHISH
# ============================================================

def open_grid() -> list:
    """
    Joriy narx atrofida grid ochish:
    - 6 ta BUY: joriy narxdan PASTGA, 20 point oralig'ida
    - 6 ta SELL: joriy narxdan YUQORIGA, 20 point oralig'ida

    Grid sxemasi (XAUUSD ~4076):
    SELL 6  → 4076 + 6*20*point = 4077.20
    SELL 5  → 4076 + 5*20*point = 4077.00
    SELL 4  → 4076 + 4*20*point = 4076.80
    SELL 3  → 4076 + 3*20*point = 4076.60
    SELL 2  → 4076 + 2*20*point = 4076.40
    SELL 1  → 4076 + 1*20*point = 4076.20
    ────── JORIY NARX: 4076.00 ──────
    BUY  1  → 4076 - 1*20*point = 4075.80
    BUY  2  → 4076 - 2*20*point = 4075.60
    BUY  3  → 4076 - 3*20*point = 4075.40
    BUY  4  → 4076 - 4*20*point = 4075.20
    BUY  5  → 4076 - 5*20*point = 4075.00
    BUY  6  → 4076 - 6*20*point = 4074.80
    """
    ensure_symbol()
    tick = get_tick()
    if tick is None:
        return []

    point      = get_point()
    mid_price  = (tick.bid + tick.ask) / 2
    step_price = GRID_STEP * point

    logger.info("=" * 58)
    logger.info(f"🚀 GRID OCHILMOQDA")
    logger.info(f"   Narx: {mid_price:.5f} | Step: {step_price:.5f} | Point: {point}")
    logger.info(f"   {BUY_COUNT} BUY (pastda) + {SELL_COUNT} SELL (yuqorida)")
    logger.info("=" * 58)

    opened = []

    # --- 6 ta SELL (joriy narxdan yuqorida) ---
    logger.info(f"📉 SELL grid ({SELL_COUNT} ta, yuqorida)...")
    for i in range(1, SELL_COUNT + 1):
        grid_price = mid_price + i * step_price
        result = open_order("sell", grid_price)
        if result:
            opened.append(result)
            logger.info(f"  SELL {i}/{SELL_COUNT} | Grid narx: {grid_price:.5f}")
        time.sleep(0.2)

    # --- 6 ta BUY (joriy narxdan pastda) ---
    logger.info(f"📈 BUY grid ({BUY_COUNT} ta, pastda)...")
    for i in range(1, BUY_COUNT + 1):
        grid_price = mid_price - i * step_price
        result = open_order("buy", grid_price)
        if result:
            opened.append(result)
            logger.info(f"  BUY  {i}/{BUY_COUNT} | Grid narx: {grid_price:.5f}")
        time.sleep(0.2)

    logger.info(f"✅ Jami {len(opened)}/{BUY_COUNT + SELL_COUNT} pozitsiya ochildi")
    return opened


# ============================================================
#  OCHIQ POZITSIYALAR
# ============================================================

def get_positions() -> list:
    """Faqat bu bot ochgan pozitsiyalarni qaytarish"""
    positions = mt5.positions_get(symbol=SYMBOL)
    if positions is None:
        return []
    return [p for p in positions if p.magic == MAGIC]


def count_positions() -> dict:
    positions = get_positions()
    buy  = sum(1 for p in positions if p.type == mt5.ORDER_TYPE_BUY)
    sell = sum(1 for p in positions if p.type == mt5.ORDER_TYPE_SELL)
    return {"buy": buy, "sell": sell, "total": len(positions)}


# ============================================================
#  JAMI FOYDA HISOBLASH
# ============================================================

def get_total_profit() -> float:
    positions = get_positions()
    if not positions:
        return 0.0
    return round(sum(p.profit for p in positions), 4)


# ============================================================
#  BITTA POZITSIYANI YOPISH
# ============================================================

def close_position(pos) -> bool:
    tick = get_tick()
    if tick is None:
        return False

    if pos.type == mt5.ORDER_TYPE_BUY:
        order_type = mt5.ORDER_TYPE_SELL
        price      = tick.bid
    else:
        order_type = mt5.ORDER_TYPE_BUY
        price      = tick.ask

    request = {
        "action":       mt5.TRADE_ACTION_DEAL,
        "symbol":       SYMBOL,
        "volume":       pos.volume,
        "type":         order_type,
        "position":     pos.ticket,
        "price":        price,
        "deviation":    30,
        "magic":        MAGIC,
        "comment":      "grid_close",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        code = result.retcode if result else "None"
        logger.error(f"Yopishda xato | ticket: {pos.ticket} | retcode: {code}")
        return False

    logger.info(f"✅ Yopildi | ticket: {pos.ticket} | foyda: {pos.profit:.4f}$")
    return True


# ============================================================
#  BARCHA POZITSIYALARNI YOPISH
# ============================================================

def close_all() -> int:
    positions = get_positions()
    if not positions:
        logger.info("Yopiladigan pozitsiya yo'q")
        return 0
    closed = 0
    for pos in positions:
        if close_position(pos):
            closed += 1
        time.sleep(0.15)
    logger.info(f"🔒 {closed}/{len(positions)} pozitsiya yopildi")
    return closed


# ============================================================
#  FOYDA KUTISH VA YOPISH
# ============================================================

def monitor_and_close() -> float:
    """
    Har CHECK_INTERVAL soniyada foyda tekshiriladi.
    Foyda >= $5 bo'lsa → hammasi yopiladi.
    """
    logger.info(f"⏳ Monitoring boshlandi | Maqsad: ${PROFIT_TARGET}")
    check = 0

    while True:
        time.sleep(CHECK_INTERVAL)
        check += 1

        counts = count_positions()
        if counts["total"] == 0:
            logger.warning("⚠️  Pozitsiya qolmadi! Yangi grid boshlanadi...")
            return 0.0

        pnl = get_total_profit()

        # Status log
        status = "📈" if pnl >= 0 else "📉"
        logger.info(
            f"[#{check}] {status} PnL: {pnl:+.4f}$ | "
            f"Maqsad: ${PROFIT_TARGET} | "
            f"Pos: {counts['total']} (B:{counts['buy']} S:{counts['sell']})"
        )

        # Zarar haqida ogohlantirish (lekin yopmaymiz)
        if pnl <= MAX_LOSS:
            logger.warning(f"⚠️  Zarar: {pnl:.4f}$ | Davom etilmoqda (limit: ${MAX_LOSS})")

        # Maqsadga yetildi!
        if pnl >= PROFIT_TARGET:
            logger.info(f"🎯 MAQSAD! Foyda: ${pnl:.4f} → Yopilmoqda...")
            closed = close_all()
            logger.info(f"✅ {closed} pozitsiya yopildi | Foyda: ${pnl:.4f}")
            return pnl


# ============================================================
#  ASOSIY BOT SIKLI
# ============================================================

def run_grid_bot():
    print("=" * 58)
    print("   🤖 GRID TRADING BOT — XAUUSD")
    print(f"   {BUY_COUNT} BUY + {SELL_COUNT} SELL | Grid: {GRID_STEP} pt | Maqsad: ${PROFIT_TARGET}")
    print("=" * 58)

    # MT5 ga ulanish
    if not connect():
        logger.error("❌ MT5 ga ulanib bo'lmadi!")
        return

    sikl      = 0
    jami_pnl  = 0.0

    try:
        while True:
            sikl += 1
            logger.info(f"\n{'='*58}")
            logger.info(f"  📊 GRID SIKL #{sikl} | Jami foyda: ${jami_pnl:.4f}")
            logger.info(f"{'='*58}")

            # 1) Grid ochish
            opened = open_grid()

            if len(opened) < (BUY_COUNT + SELL_COUNT) // 2:
                logger.error(f"❌ Yetarli grid ochilmadi ({len(opened)} ta). 15s kutilmoqda...")
                close_all()
                time.sleep(15)
                continue

            # 2) Foyda monitoring va yopish
            profit = monitor_and_close()
            jami_pnl += profit

            logger.info(f"🏁 Sikl #{sikl} tugadi | Foyda: ${profit:.4f} | Jami: ${jami_pnl:.4f}")
            logger.info("⏸️  3 soniya pauza...")
            time.sleep(3)

    except KeyboardInterrupt:
        logger.info("\n🛑 Bot to'xtatildi (Ctrl+C)")
        logger.info("Barcha pozitsiyalar yopilmoqda...")
        close_all()
        logger.info(f"✅ Tozalandi | Jami foyda: ${jami_pnl:.4f}")
    finally:
        disconnect()


if __name__ == "__main__":
    run_grid_bot()
