# ================================================================
#  RISK_MANAGER.PY — RISK MENEJMENT
#  Lot hisoblash, SL/TP, Trailing Stop, Kunlik limit
# ================================================================

import MetaTrader5 as mt5
import logging
from datetime import datetime, timezone
from config import (
    SYMBOL, MAGIC, BALANCE, RISK_PER_TRADE,
    MAX_DAILY_LOSS, DAILY_PROFIT_TARGET,
    ATR_SL_MULT, ATR_TP_MULT, TRAILING_STEP,
    MIN_LOT, MAX_LOT, LOT_STEP
)

logger = logging.getLogger(__name__)

# Kunlik statistika
_daily_stats = {
    "date":          None,
    "profit":        0.0,
    "loss":          0.0,
    "trades":        0,
    "wins":          0,
    "losses":        0,
}


# ================================================================
#  KUNLIK STATISTIKANI YANGILASH
# ================================================================
def reset_daily_if_needed():
    """Yangi kun boshlanganida statistikani tozalash"""
    today = datetime.now(timezone.utc).date()
    if _daily_stats["date"] != today:
        _daily_stats.update({
            "date":    today,
            "profit":  0.0,
            "loss":    0.0,
            "trades":  0,
            "wins":    0,
            "losses":  0,
        })
        logger.info(f"📅 Yangi kun: {today} | Statistika tozalandi")


def update_daily_stats(profit: float):
    """Yopilgan pozitsiya natijasini qo'shish"""
    reset_daily_if_needed()
    _daily_stats["trades"] += 1
    if profit > 0:
        _daily_stats["profit"] += profit
        _daily_stats["wins"]   += 1
    else:
        _daily_stats["loss"]   += abs(profit)
        _daily_stats["losses"] += 1


def get_daily_stats() -> dict:
    reset_daily_if_needed()
    net = _daily_stats["profit"] - _daily_stats["loss"]
    winrate = (
        _daily_stats["wins"] / _daily_stats["trades"] * 100
        if _daily_stats["trades"] > 0 else 0
    )
    return {**_daily_stats, "net": round(net, 4), "winrate": round(winrate, 1)}


# ================================================================
#  KUNLIK LIMIT TEKSHIRISH
# ================================================================
def check_daily_limits() -> dict:
    """
    Kunlik zarar yoki foyda limitiga yetilganmi?
    Returns: {"can_trade": bool, "reason": str}
    """
    reset_daily_if_needed()
    stats = get_daily_stats()

    # Hisob balansini olish
    account = mt5.account_info()
    balance = account.balance if account else BALANCE

    max_loss_usd   = balance * MAX_DAILY_LOSS
    daily_net      = stats["net"]

    # Kunlik zarar limiti
    if daily_net <= -max_loss_usd:
        return {
            "can_trade": False,
            "reason":    f"Kunlik zarar limiti: {daily_net:.2f}$ (limit: -{max_loss_usd:.2f}$)"
        }

    # Kunlik foyda maqsadiga yetildi
    if daily_net >= DAILY_PROFIT_TARGET:
        return {
            "can_trade": False,
            "reason":    f"Kunlik maqsadga yetildi! Foyda: {daily_net:.2f}$ (maqsad: ${DAILY_PROFIT_TARGET})"
        }

    return {
        "can_trade": True,
        "reason":    f"OK | Net: {daily_net:+.2f}$ | Limit: -{max_loss_usd:.2f}$"
    }


# ================================================================
#  LOT HISOBLASH (Risk asosida)
# ================================================================
def calc_lot(atr: float) -> float:
    """
    ATR va risk foiziga asosan optimal lot hisoblash
    Formula: Lot = (Balance × Risk%) / (ATR × SL_multiplier × ContractSize)
    XAUUSD contract size = 100 oz
    """
    account = mt5.account_info()
    balance = account.balance if account else BALANCE

    risk_amount = balance * RISK_PER_TRADE   # masalan $10

    if atr <= 0:
        return MIN_LOT

    # XAUUSD: 1 lot = 100 oz, 1 pip = $1 per 0.01 lot
    sl_pips = atr * ATR_SL_MULT
    sym_info = mt5.symbol_info(SYMBOL)
    if sym_info is None:
        return MIN_LOT

    # pip value per lot
    pip_value = sym_info.trade_tick_value / sym_info.trade_tick_size

    if pip_value <= 0 or sl_pips <= 0:
        return MIN_LOT

    lot = risk_amount / (sl_pips * pip_value)

    # Chegaralash
    lot = max(MIN_LOT, min(lot, MAX_LOT))

    # LOT_STEP ga yaxlitlash
    lot = round(round(lot / LOT_STEP) * LOT_STEP, 2)

    logger.debug(
        f"Lot hisob | Balance: {balance:.0f}$ | Risk: {risk_amount:.2f}$ | "
        f"ATR: {atr:.5f} | SL pips: {sl_pips:.5f} | Lot: {lot}"
    )
    return lot


# ================================================================
#  SL / TP HISOBLASH
# ================================================================
def calc_sl_tp(direction: str, entry_price: float, atr: float) -> dict:
    """
    ATR asosida SL va TP hisoblash
    BUY:  SL = entry - ATR*1.5  |  TP = entry + ATR*3.0
    SELL: SL = entry + ATR*1.5  |  TP = entry - ATR*3.0
    """
    sym_info = mt5.symbol_info(SYMBOL)
    digits   = sym_info.digits if sym_info else 2

    # ATR 0 yoki juda kichik bo'lsa — H1 dan hisoblash
    if atr <= 0:
        logger.warning("⚠️  ATR 0! H1 dan qayta hisoblanmoqda...")
        rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 20)
        if rates is not None and len(rates) >= 15:
            tr_list = [
                max(rates["high"][i] - rates["low"][i],
                    abs(rates["high"][i] - rates["close"][i-1]),
                    abs(rates["low"][i]  - rates["close"][i-1]))
                for i in range(1, len(rates))
            ]
            atr = sum(tr_list[-14:]) / 14
        else:
            # Oxirgi chora: narxning 0.5% ini ishlatish
            atr = entry_price * 0.005
        logger.info(f"   Yangi ATR: {atr:.5f}")

    sl_dist = atr * ATR_SL_MULT
    tp_dist = atr * ATR_TP_MULT

    # Minimal SL/TP masofasi (spread dan kam bo'lmasin)
    if sym_info:
        min_dist = sym_info.spread * sym_info.point * 3
        sl_dist  = max(sl_dist, min_dist)
        tp_dist  = max(tp_dist, min_dist * 2)

    if direction == "BUY":
        sl = round(entry_price - sl_dist, digits)
        tp = round(entry_price + tp_dist, digits)
    else:
        sl = round(entry_price + sl_dist, digits)
        tp = round(entry_price - tp_dist, digits)

    logger.info(
        f"📐 SL/TP | {direction} | Entry: {entry_price:.5f} | "
        f"SL: {sl:.5f} (−{sl_dist:.5f}) | "
        f"TP: {tp:.5f} (+{tp_dist:.5f}) | "
        f"R:R = 1:{round(tp_dist/sl_dist, 1) if sl_dist > 0 else 0}"
    )

    return {
        "sl":      sl,
        "tp":      tp,
        "sl_dist": round(sl_dist, 5),
        "tp_dist": round(tp_dist, 5),
        "rr_ratio": round(tp_dist / sl_dist, 2) if sl_dist > 0 else 0
    }


# ================================================================
#  TRAILING STOP YANGILASH
# ================================================================
def update_trailing_stops() -> int:
    """
    Barcha ochiq pozitsiyalar uchun trailing stop yangilash.
    Narx SL tomonga {TRAILING_STEP * ATR} harakat qilsa SL ko'tariladi.
    Returns: yangilangan pozitsiyalar soni
    """
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return 0

    updated = 0
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        return 0

    sym_info = mt5.symbol_info(SYMBOL)
    digits = sym_info.digits if sym_info else 5

    for pos in positions:
        if pos.magic != MAGIC:
            continue

        # ATR hisoblash (H1 dan)
        rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 20)
        if rates is None or len(rates) < 15:
            continue

        highs  = rates["high"]
        lows   = rates["low"]
        closes = rates["close"]

        tr_list = [
            max(highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1]))
            for i in range(1, len(closes))
        ]
        atr = sum(tr_list[-14:]) / 14
        trail_dist = atr * TRAILING_STEP

        if pos.type == mt5.ORDER_TYPE_BUY:
            new_sl = round(tick.bid - trail_dist, digits)
            # Faqat SL ko'tarilsa yangilash (pastga tushmaydi)
            if new_sl > pos.sl + atr * 0.1:
                _modify_sl(pos.ticket, new_sl, pos.tp)
                updated += 1

        elif pos.type == mt5.ORDER_TYPE_SELL:
            new_sl = round(tick.ask + trail_dist, digits)
            # Faqat SL pastlasa yangilash
            if pos.sl == 0 or new_sl < pos.sl - atr * 0.1:
                _modify_sl(pos.ticket, new_sl, pos.tp)
                updated += 1

    if updated > 0:
        logger.info(f"🔄 Trailing stop yangilandi: {updated} ta pozitsiya")
    return updated


def _modify_sl(ticket: int, new_sl: float, tp: float) -> bool:
    """Pozitsiya SL ni o'zgartirish"""
    request = {
        "action":   mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "symbol":   SYMBOL,
        "sl":       new_sl,
        "tp":       tp,
    }
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        logger.debug(f"Trailing SL yangilandi | ticket: {ticket} | new_sl: {new_sl}")
        return True
    return False


# ================================================================
#  POZITSIYA FOYDA/ZARAR HISOBOTI
# ================================================================
def get_position_summary() -> dict:
    """Barcha ochiq pozitsiyalar umumiy hisoboti"""
    positions = mt5.positions_get(symbol=SYMBOL)
    if not positions:
        return {"total": 0, "buy": 0, "sell": 0, "unrealized_pnl": 0.0}

    bot_positions = [p for p in positions if p.magic == MAGIC]
    buy_pos  = [p for p in bot_positions if p.type == mt5.ORDER_TYPE_BUY]
    sell_pos = [p for p in bot_positions if p.type == mt5.ORDER_TYPE_SELL]
    total_pnl = sum(p.profit for p in bot_positions)

    return {
        "total":          len(bot_positions),
        "buy":            len(buy_pos),
        "sell":           len(sell_pos),
        "unrealized_pnl": round(total_pnl, 4),
        "buy_pnl":        round(sum(p.profit for p in buy_pos), 4),
        "sell_pnl":       round(sum(p.profit for p in sell_pos), 4),
    }
