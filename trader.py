# ================================================================
#  TRADER.PY — MT5 SAVDO MODULI
#  Ulanish, buyurtma ochish/yopish, pozitsiyalar boshqarish
# ================================================================

import MetaTrader5 as mt5
import time
import logging
from config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, SYMBOL, MAGIC

logger = logging.getLogger(__name__)


# ================================================================
#  ULANISH
# ================================================================
def connect() -> bool:
    if not mt5.initialize():
        logger.error(f"❌ MT5 initialize: {mt5.last_error()}")
        return False

    ok = mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
    if not ok:
        logger.error(f"❌ MT5 login: {mt5.last_error()}")
        mt5.shutdown()
        return False

    acc = mt5.account_info()
    logger.info(
        f"✅ MT5 ulandi | #{acc.login} | "
        f"Balans: {acc.balance:.2f}$ | "
        f"Leverage: 1:{acc.leverage} | "
        f"Server: {acc.server}"
    )

    # Symbol tekshirish
    sym = mt5.symbol_info(SYMBOL)
    if sym is None or not sym.visible:
        mt5.symbol_select(SYMBOL, True)
        time.sleep(0.5)
        logger.info(f"✅ {SYMBOL} Market Watch ga qo'shildi")

    return True


def disconnect():
    mt5.shutdown()
    logger.info("MT5 ulanishi uzildi")


# ================================================================
#  NARX OLISH
# ================================================================
def get_tick() -> dict | None:
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        logger.error(f"Tick olinmadi: {mt5.last_error()}")
        return None
    return {"bid": tick.bid, "ask": tick.ask, "spread": tick.ask - tick.bid}


# ================================================================
#  BUYURTMA OCHISH (SL/TP bilan)
# ================================================================
def _get_filling_mode() -> int:
    """
    MT5 server qo'llab-quvvatlaydigan filling modeni aniqlash.
    MetaQuotes-Demo ko'pincha RETURN yoki IOC ishlatadi.
    """
    sym_info = mt5.symbol_info(SYMBOL)
    if sym_info is None:
        return mt5.ORDER_FILLING_IOC

    filling_mode = sym_info.filling_mode

    # 1 = FOK, 2 = IOC, 4 = RETURN
    if filling_mode & 4:    # RETURN — eng keng qo'llab-quvvatlanadigan
        return mt5.ORDER_FILLING_RETURN
    elif filling_mode & 2:  # IOC
        return mt5.ORDER_FILLING_IOC
    elif filling_mode & 1:  # FOK
        return mt5.ORDER_FILLING_FOK
    else:
        return mt5.ORDER_FILLING_RETURN


def open_order(direction: str, lot: float, sl: float, tp: float,
               comment: str = "pro_bot") -> dict | None:
    """
    direction: 'BUY' yoki 'SELL'
    lot: lot hajmi
    sl: stop loss narxi
    tp: take profit narxi
    """
    tick = get_tick()
    if tick is None:
        return None

    sym_info = mt5.symbol_info(SYMBOL)
    if sym_info is None:
        return None

    # SL/TP nol bo'lmasligi tekshirish
    if sl <= 0 or tp <= 0:
        logger.error(f"❌ SL yoki TP nol! SL:{sl} TP:{tp} — savdo ochilmadi")
        return None

    filling = _get_filling_mode()

    if direction.upper() == "BUY":
        order_type = mt5.ORDER_TYPE_BUY
        price      = tick["ask"]
        # SL narxdan past, TP narxdan yuqori bo'lishi kerak
        if sl >= price:
            logger.error(f"❌ BUY SL ({sl}) narxdan ({price}) yuqori!")
            return None
        if tp <= price:
            logger.error(f"❌ BUY TP ({tp}) narxdan ({price}) past!")
            return None
    else:
        order_type = mt5.ORDER_TYPE_SELL
        price      = tick["bid"]
        # SL narxdan yuqori, TP narxdan past bo'lishi kerak
        if sl <= price:
            logger.error(f"❌ SELL SL ({sl}) narxdan ({price}) past!")
            return None
        if tp >= price:
            logger.error(f"❌ SELL TP ({tp}) narxdan ({price}) yuqori!")
            return None

    request = {
        "action":       mt5.TRADE_ACTION_DEAL,
        "symbol":       SYMBOL,
        "volume":       float(lot),
        "type":         order_type,
        "price":        price,
        "sl":           float(sl),
        "tp":           float(tp),
        "deviation":    50,
        "magic":        MAGIC,
        "comment":      comment[:31],
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": filling,
    }

    result = mt5.order_send(request)

    if result is None:
        logger.error(f"❌ order_send None | {mt5.last_error()}")
        return None

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(
            f"❌ {direction} xato | retcode: {result.retcode} | "
            f"comment: {result.comment}"
        )
        # Agar filling xatosi bo'lsa RETURN bilan qayta urinish
        if result.retcode == 10030:
            logger.info("🔄 Filling xatosi, RETURN bilan qayta urinilmoqda...")
            request["type_filling"] = mt5.ORDER_FILLING_RETURN
            result = mt5.order_send(request)
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                return None
        else:
            return None

    logger.info(
        f"✅ {direction} ochildi | "
        f"Ticket: {result.order} | "
        f"Narx: {price:.5f} | "
        f"Lot: {lot} | "
        f"SL: {sl:.5f} | TP: {tp:.5f}"
    )

    return {
        "ticket":    result.order,
        "direction": direction.upper(),
        "price":     price,
        "lot":       lot,
        "sl":        sl,
        "tp":        tp
    }


# ================================================================
#  BITTA POZITSIYANI YOPISH
# ================================================================
def close_position(position) -> dict:
    """Berilgan pozitsiyani yopish"""
    tick = get_tick()
    if tick is None:
        return {"success": False, "profit": 0}

    filling = _get_filling_mode()

    if position.type == mt5.ORDER_TYPE_BUY:
        order_type = mt5.ORDER_TYPE_SELL
        price      = tick["bid"]
    else:
        order_type = mt5.ORDER_TYPE_BUY
        price      = tick["ask"]

    request = {
        "action":       mt5.TRADE_ACTION_DEAL,
        "symbol":       SYMBOL,
        "volume":       position.volume,
        "type":         order_type,
        "position":     position.ticket,
        "price":        price,
        "deviation":    30,
        "magic":        MAGIC,
        "comment":      "pro_close",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": filling,
    }

    result = mt5.order_send(request)

    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        code = result.retcode if result else "None"
        logger.error(f"❌ Yopishda xato | ticket: {position.ticket} | retcode: {code}")
        return {"success": False, "profit": 0}

    profit = position.profit
    logger.info(
        f"✅ Yopildi | Ticket: {position.ticket} | "
        f"Foyda: {profit:+.4f}$"
    )
    return {"success": True, "profit": profit}


# ================================================================
#  BARCHA POZITSIYALARNI YOPISH
# ================================================================
def close_all_positions() -> dict:
    """Bot tomonidan ochilgan barcha pozitsiyalarni yopish"""
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return {"closed": 0, "total_profit": 0.0}

    bot_positions = [p for p in positions if p.magic == MAGIC]
    if not bot_positions:
        return {"closed": 0, "total_profit": 0.0}

    closed      = 0
    total_profit = 0.0

    for pos in bot_positions:
        result = close_position(pos)
        if result["success"]:
            closed       += 1
            total_profit += result["profit"]
        time.sleep(0.15)

    logger.info(f"🔒 Yopildi: {closed}/{len(bot_positions)} | Jami: {total_profit:+.4f}$")
    return {"closed": closed, "total_profit": round(total_profit, 4)}


# ================================================================
#  OCHIQ POZITSIYALAR
# ================================================================
def get_open_positions() -> list:
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return []
    return [p for p in positions if p.magic == MAGIC]


def get_unrealized_pnl() -> float:
    positions = get_open_positions()
    return round(sum(p.profit for p in positions), 4)


def count_positions() -> dict:
    positions = get_open_positions()
    buy  = sum(1 for p in positions if p.type == mt5.ORDER_TYPE_BUY)
    sell = sum(1 for p in positions if p.type == mt5.ORDER_TYPE_SELL)
    return {"total": len(positions), "buy": buy, "sell": sell}


# ================================================================
#  HISOB MA'LUMOTLARI
# ================================================================
def get_account_info() -> dict | None:
    acc = mt5.account_info()
    if acc is None:
        return None
    return {
        "login":    acc.login,
        "balance":  acc.balance,
        "equity":   acc.equity,
        "margin":   acc.margin,
        "free_margin": acc.margin_free,
        "profit":   acc.profit,
        "leverage": acc.leverage
    }
