# ================================================================
#  BOT.PY — ASOSIY BOT MANTIQ
#  Multi-Timeframe + 8 Indikator + Risk Menejment + News Filter
#  $1000 kapital | $20-50 kunlik maqsad | 24/7
# ================================================================

import time
import logging
from datetime import datetime, timezone

import trader
import risk_manager
from timeframe_analysis import multi_timeframe_analysis, get_current_session
from news_filter import is_near_news, check_spread
from config import (
    SYMBOL, CHECK_INTERVAL, MAX_POSITIONS,
    MIN_SIGNALS, DAILY_PROFIT_TARGET, MAX_DAILY_LOSS, BALANCE
)
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)


# ================================================================
#  BANNER
# ================================================================
def print_banner():
    print("\n" + "=" * 62)
    print("   🤖 PROFESSIONAL XAUUSD BOT — Multi-TF + 8 Indikator")
    print("   💰 Kapital: $1000  |  🎯 Maqsad: $20-50/kun  |  24/7")
    print("=" * 62)
    print("   📊 Indikatorlar: EMA · RSI · MACD · Stoch · BB · ATR")
    print("                   Supertrend · OBV")
    print("   ⏱️  Timeframlar:  M1 · H1 · D1 · W1")
    print("   🛡️  Risk:         ATR-SL · Trailing · Kunlik limit")
    print("   📰 Filter:       News · Spread · Sessiya")
    print("=" * 62 + "\n")


# ================================================================
#  SIGNAL TEKSHIRISH
# ================================================================
def check_signal() -> dict:
    """
    Barcha filtrlardan o'tib signal tekshirish
    Returns: {"action": "BUY"/"SELL"/"WAIT", "reason": str, "atr": float}
    """

    # 1) Kunlik limit
    limit = risk_manager.check_daily_limits()
    if not limit["can_trade"]:
        return {"action": "WAIT", "reason": limit["reason"], "atr": 0}

    # 2) Max pozitsiya soni
    counts = trader.count_positions()
    if counts["total"] >= MAX_POSITIONS:
        return {
            "action": "WAIT",
            "reason": f"Max pozitsiya: {counts['total']}/{MAX_POSITIONS}",
            "atr": 0
        }

    # 3) News filter
    news = is_near_news()
    if news["blocked"]:
        return {"action": "WAIT", "reason": f"📰 {news['reason']}", "atr": 0}

    # 4) Spread tekshirish
    sym_info = mt5.symbol_info(SYMBOL)
    spread_check = check_spread(sym_info)
    if not spread_check["ok"]:
        return {"action": "WAIT", "reason": spread_check["reason"], "atr": 0}

    # 5) Sessiya tekshirish
    session = get_current_session()
    if not session["is_trading_time"]:
        return {
            "action": "WAIT",
            "reason": f"Off-hours ({session['session_name']})",
            "atr": 0
        }

    # 6) Multi-Timeframe tahlil
    mtf = multi_timeframe_analysis()
    signal  = mtf["signal"]
    conf    = mtf["confidence"]
    aligned = mtf["trend_aligned"]
    atr     = mtf["atr"]

    if signal == "NONE":
        return {
            "action": "WAIT",
            "reason": f"Signal yo'q (BUY:{mtf['weighted_buy']:.3f} SELL:{mtf['weighted_sell']:.3f})",
            "atr": atr
        }

    # 7) Signal kuchini tekshirish
    if conf < 0.3:
        return {
            "action": "WAIT",
            "reason": f"Signal kuchsiz: {conf:.3f} < 0.30",
            "atr": atr
        }

    # 8) Trend alignment bonus
    quality = "KUCHLI ✅" if aligned and conf > 0.5 else "O'RTA ⚠️"

    return {
        "action":    signal,
        "reason":    f"{signal} | Ishonch: {conf:.3f} | {quality}",
        "atr":       atr,
        "confidence": conf,
        "aligned":   aligned,
        "mtf":       mtf
    }


# ================================================================
#  SAVDO OCHISH
# ================================================================
def open_trade(signal: dict) -> bool:
    """Signal asosida pozitsiya ochish"""
    direction = signal["action"]
    atr       = signal["atr"]

    if atr <= 0:
        logger.warning("ATR nol, savdo ochilmadi")
        return False

    # Lot hisoblash
    lot = risk_manager.calc_lot(atr)

    # Joriy narx
    tick = trader.get_tick()
    if tick is None:
        return False

    entry = tick["ask"] if direction == "BUY" else tick["bid"]

    # SL/TP hisoblash
    sl_tp = risk_manager.calc_sl_tp(direction, entry, atr)

    # Buyurtma yuborish
    result = trader.open_order(
        direction = direction,
        lot       = lot,
        sl        = sl_tp["sl"],
        tp        = sl_tp["tp"],
        comment   = f"mtf_{direction[:1]}_{int(signal['confidence']*100)}"
    )

    if result:
        logger.info(
            f"🎯 SAVDO OCHILDI | {direction} | "
            f"Lot: {lot} | Entry: {entry:.5f} | "
            f"SL: {sl_tp['sl']:.5f} | TP: {sl_tp['tp']:.5f} | "
            f"R:R = 1:{sl_tp['rr_ratio']}"
        )
        return True

    return False


# ================================================================
#  HOLAT HISOBOTI (har 10 siklda)
# ================================================================
def print_status(cycle: int):
    """Bot holati va statistikani chiqarish"""
    acc     = trader.get_account_info()
    counts  = trader.count_positions()
    pnl     = trader.get_unrealized_pnl()
    stats   = risk_manager.get_daily_stats()
    session = get_current_session()

    if acc is None:
        return

    logger.info("─" * 62)
    logger.info(
        f"📊 HOLAT #{cycle} | "
        f"Balans: {acc['balance']:.2f}$ | "
        f"Equity: {acc['equity']:.2f}$"
    )
    logger.info(
        f"   Pozitsiyalar: {counts['total']} (B:{counts['buy']} S:{counts['sell']}) | "
        f"Unrealized: {pnl:+.4f}$"
    )
    logger.info(
        f"   Bugun: Net: {stats['net']:+.4f}$ | "
        f"Savdolar: {stats['trades']} | "
        f"Winrate: {stats['winrate']:.0f}%"
    )
    logger.info(
        f"   Sessiya: {session['session_name']} | "
        f"Vaqt UTC: {datetime.now(timezone.utc).strftime('%H:%M:%S')}"
    )
    logger.info("─" * 62)


# ================================================================
#  ASOSIY BOT SIKLI
# ================================================================
def run_bot():
    """Asosiy bot loop — to'xtatilgunga qadar ishlaydi"""
    print_banner()

    # MT5 ga ulanish
    if not trader.connect():
        logger.error("❌ MT5 ga ulanib bo'lmadi! main.py ni qayta ishga tushiring.")
        return

    logger.info("✅ Bot ishga tushdi | Signal kutilmoqda...\n")

    cycle        = 0
    last_status  = 0

    try:
        while True:
            cycle += 1
            now = datetime.now(timezone.utc)

            # ── Har 10 siklda holat hisoboti ──
            if cycle - last_status >= 10:
                print_status(cycle)
                last_status = cycle

            # ── Trailing stop yangilash ──
            if cycle % 3 == 0:
                risk_manager.update_trailing_stops()

            # ── Signal tekshirish ──
            signal = check_signal()

            if signal["action"] in ("BUY", "SELL"):
                logger.info(f"\n🔔 SIGNAL: {signal['reason']}")
                success = open_trade(signal)
                if success:
                    time.sleep(5)   # Pozitsiya ochilgandan keyin qisqa pauza

            else:
                # Har 30 siklda WAIT sababini ko'rsat
                if cycle % 30 == 0:
                    logger.info(f"⏳ KUTISH: {signal['reason']}")

            # ── CHECK_INTERVAL soniya kutish ──
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        logger.info("\n🛑 Bot to'xtatildi (Ctrl+C)")
        logger.info("Barcha pozitsiyalar yopilmoqda...")
        result = trader.close_all_positions()
        stats  = risk_manager.get_daily_stats()
        logger.info(f"✅ {result['closed']} pozitsiya yopildi | Kunlik net: {stats['net']:+.4f}$")

    except Exception as e:
        logger.exception(f"❌ Kutilmagan xato: {e}")
        logger.info("Xavfsizlik uchun barcha pozitsiyalar yopilmoqda...")
        trader.close_all_positions()

    finally:
        trader.disconnect()
        logger.info("Bot to'xtatildi. Xayr! 👋")
