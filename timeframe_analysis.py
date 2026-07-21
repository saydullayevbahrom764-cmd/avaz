# ================================================================
#  TIMEFRAME_ANALYSIS.PY — 4 TIMEFRAME TAHLIL
#  M1, H1, D1, W1 — har birida 8 ta indikator tekshiriladi
# ================================================================

import MetaTrader5 as mt5
import numpy as np
import logging
from indicators import get_all_signals, calc_atr
from config import SYMBOL, TF_WEIGHTS, MIN_SIGNALS

logger = logging.getLogger(__name__)

# MT5 Timeframe konstantlari
TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1,
    "H1": mt5.TIMEFRAME_H1,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
}

# Har timeframe uchun nechta sham olish
CANDLE_COUNTS = {
    "M1": 300,
    "H1": 300,
    "D1": 300,
    "W1": 200,
}


# ================================================================
#  MT5 DAN SHAM MA'LUMOTLARI OLISH
# ================================================================
def get_candles(timeframe_key: str) -> dict | None:
    """
    Berilgan timeframe uchun sham ma'lumotlarini olish
    Returns: {"highs", "lows", "closes", "volumes", "times"}
    """
    tf    = TIMEFRAMES.get(timeframe_key)
    count = CANDLE_COUNTS.get(timeframe_key, 300)

    if tf is None:
        logger.error(f"Noto'g'ri timeframe: {timeframe_key}")
        return None

    rates = mt5.copy_rates_from_pos(SYMBOL, tf, 0, count)

    if rates is None or len(rates) == 0:
        logger.warning(f"Shamlar olinmadi: {timeframe_key} | {mt5.last_error()}")
        return None

    return {
        "highs":   rates["high"],
        "lows":    rates["low"],
        "closes":  rates["close"],
        "opens":   rates["open"],
        "volumes": rates["tick_volume"],
        "times":   rates["time"],
        "count":   len(rates)
    }


# ================================================================
#  BITTA TIMEFRAME TAHLIL
# ================================================================
def analyze_timeframe(tf_key: str) -> dict:
    """
    Bir timeframe uchun barcha 8 ta indikatorni hisoblash
    Returns: signal natijasi va kuch ko'rsatkichi
    """
    candles = get_candles(tf_key)

    if candles is None:
        return {
            "timeframe": tf_key,
            "signal":    "NONE",
            "score":     0,
            "signals":   {},
            "atr":       0,
            "error":     True
        }

    signals = get_all_signals(
        candles["highs"],
        candles["lows"],
        candles["closes"],
        candles["volumes"]
    )

    summary = signals["summary"]
    atr     = signals.get("atr", 0)

    # Dominant signal aniqlash
    dominant = summary["dominant"]
    score    = 0

    if dominant == "BUY":
        score = summary["buy_strength"] / max(summary["buy_count"], 1)
    elif dominant == "SELL":
        score = summary["sell_strength"] / max(summary["sell_count"], 1)

    logger.debug(
        f"[{tf_key}] Signal: {dominant} | "
        f"BUY:{summary['buy_count']} SELL:{summary['sell_count']} | "
        f"Score: {score:.3f}"
    )

    return {
        "timeframe":    tf_key,
        "signal":       dominant,
        "score":        round(score, 3),
        "buy_count":    summary["buy_count"],
        "sell_count":   summary["sell_count"],
        "buy_strength": summary["buy_strength"],
        "sell_strength":summary["sell_strength"],
        "signals":      signals,
        "atr":          atr,
        "error":        False
    }


# ================================================================
#  4 TIMEFRAME KOMBINATSIYA TAHLILI
# ================================================================
def multi_timeframe_analysis() -> dict:
    """
    4 timeframe (M1, H1, D1, W1) ni tahlil qilib
    vazn asosida umumiy signal chiqarish

    Logika:
    - W1 va D1 → katta trend yo'nalishi (og'irroq)
    - H1        → asosiy savdo trendi
    - M1        → kirish nuqtasi
    """
    results  = {}
    weighted_buy  = 0.0
    weighted_sell = 0.0
    total_weight  = 0.0

    logger.info("📊 Multi-Timeframe tahlil boshlanmoqda...")

    for tf_key, weight in TF_WEIGHTS.items():
        result = analyze_timeframe(tf_key)
        results[tf_key] = result

        if not result["error"]:
            if result["signal"] == "BUY":
                weighted_buy  += result["score"] * weight
            elif result["signal"] == "SELL":
                weighted_sell += result["score"] * weight
            total_weight += weight

    # Normalize
    if total_weight > 0:
        weighted_buy  /= total_weight
        weighted_sell /= total_weight

    # Umumiy signal
    if weighted_buy > weighted_sell and weighted_buy > 0.3:
        final_signal = "BUY"
        confidence   = weighted_buy
    elif weighted_sell > weighted_buy and weighted_sell > 0.3:
        final_signal = "SELL"
        confidence   = weighted_sell
    else:
        final_signal = "NONE"
        confidence   = 0.0

    # Trend kuchini hisoblash (W1 va D1 bir yo'nalishda bo'lsa kuchli)
    trend_aligned = (
        results.get("W1", {}).get("signal") ==
        results.get("D1", {}).get("signal") ==
        final_signal
    )

    # ATR — H1 dan olish (eng ishonchli)
    atr = results.get("H1", {}).get("atr", 0) or results.get("D1", {}).get("atr", 0)

    # Log chiqarish
    logger.info(
        f"📈 MTF Natija: {final_signal} | "
        f"Ishonch: {confidence:.3f} | "
        f"Trend aligned: {trend_aligned} | "
        f"ATR: {atr:.5f}"
    )

    for tf_key, r in results.items():
        if not r.get("error"):
            emoji = "📈" if r["signal"] == "BUY" else ("📉" if r["signal"] == "SELL" else "➡️")
            logger.info(
                f"  [{tf_key}] {emoji} {r['signal']} | "
                f"B:{r['buy_count']} S:{r['sell_count']} | "
                f"Score: {r['score']:.3f}"
            )

    return {
        "signal":        final_signal,
        "confidence":    round(confidence, 3),
        "weighted_buy":  round(weighted_buy, 3),
        "weighted_sell": round(weighted_sell, 3),
        "trend_aligned": trend_aligned,
        "atr":           atr,
        "timeframes":    results,
        "is_strong":     confidence > 0.5 and trend_aligned
    }


# ================================================================
#  SESSIYA TEKSHIRISH (London / New York)
# ================================================================
def get_current_session() -> dict:
    """Hozir qaysi savdo sessiyasida ekanligini aniqlash"""
    from datetime import datetime, timezone
    from config import SESSIONS, TRADE_ALL_SESSIONS

    now_utc  = datetime.now(timezone.utc)
    hour_utc = now_utc.hour

    active_sessions = []
    for s in SESSIONS:
        if s["start"] <= hour_utc < s["end"]:
            active_sessions.append(s["name"])

    is_active = TRADE_ALL_SESSIONS or len(active_sessions) > 0

    return {
        "hour_utc":       hour_utc,
        "active_sessions": active_sessions,
        "is_trading_time": is_active,
        "session_name":   ", ".join(active_sessions) if active_sessions else "Off-hours"
    }
