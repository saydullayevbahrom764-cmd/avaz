# ================================================================
#  INDICATORS.PY — 8 TA INDIKATOR HISOBLASH
#  EMA, RSI, MACD, Stochastic, Bollinger, ATR, Supertrend, OBV
# ================================================================

import numpy as np
from config import (
    EMA_FAST, EMA_SLOW, RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT,
    STOCH_K, STOCH_D, STOCH_SLOW, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    BB_PERIOD, BB_STD, ATR_PERIOD, SUPERTREND_PERIOD, SUPERTREND_MULT
)


# ================================================================
#  1. EMA — Exponential Moving Average
# ================================================================
def calc_ema(closes: np.ndarray, period: int) -> np.ndarray:
    ema = np.zeros(len(closes))
    k = 2.0 / (period + 1)
    ema[period - 1] = np.mean(closes[:period])
    for i in range(period, len(closes)):
        ema[i] = closes[i] * k + ema[i - 1] * (1 - k)
    return ema


def ema_signal(closes: np.ndarray) -> dict:
    """
    EMA50 > EMA200 → BUY (bull trend)
    EMA50 < EMA200 → SELL (bear trend)
    """
    if len(closes) < EMA_SLOW + 5:
        return {"signal": "NONE", "strength": 0}

    ema_fast = calc_ema(closes, EMA_FAST)
    ema_slow = calc_ema(closes, EMA_SLOW)

    ef = ema_fast[-1]
    es = ema_slow[-1]
    ef_prev = ema_fast[-2]
    es_prev = ema_slow[-2]

    # Kesishma tekshirish
    crossover  = ef_prev <= es_prev and ef > es   # Oltin kesishma (BUY)
    crossunder = ef_prev >= es_prev and ef < es   # O'lim kesishma (SELL)

    diff_pct = abs(ef - es) / es * 100

    if ef > es:
        signal = "BUY"
        strength = min(diff_pct * 10, 1.0)
    elif ef < es:
        signal = "SELL"
        strength = min(diff_pct * 10, 1.0)
    else:
        signal = "NONE"
        strength = 0

    return {
        "signal": signal,
        "strength": round(strength, 3),
        "ema_fast": round(ef, 5),
        "ema_slow": round(es, 5),
        "crossover": crossover,
        "crossunder": crossunder
    }


# ================================================================
#  2. RSI — Relative Strength Index
# ================================================================
def calc_rsi(closes: np.ndarray, period: int = RSI_PERIOD) -> np.ndarray:
    deltas = np.diff(closes)
    gains  = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    rsi = np.zeros(len(closes))
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi[i + 1] = 100
        else:
            rs = avg_gain / avg_loss
            rsi[i + 1] = 100 - (100 / (1 + rs))

    return rsi


def rsi_signal(closes: np.ndarray) -> dict:
    """
    RSI < 35 → BUY (oversold)
    RSI > 65 → SELL (overbought)
    """
    if len(closes) < RSI_PERIOD + 5:
        return {"signal": "NONE", "rsi": 50, "strength": 0}

    rsi = calc_rsi(closes)
    current = rsi[-1]
    prev    = rsi[-2]

    if current < RSI_OVERSOLD:
        signal   = "BUY"
        strength = (RSI_OVERSOLD - current) / RSI_OVERSOLD
    elif current > RSI_OVERBOUGHT:
        signal   = "SELL"
        strength = (current - RSI_OVERBOUGHT) / (100 - RSI_OVERBOUGHT)
    else:
        signal   = "NONE"
        strength = 0

    return {
        "signal": signal,
        "rsi": round(current, 2),
        "prev_rsi": round(prev, 2),
        "strength": round(min(strength, 1.0), 3)
    }


# ================================================================
#  3. MACD — Moving Average Convergence Divergence
# ================================================================
def macd_signal(closes: np.ndarray) -> dict:
    """
    MACD chiziq Signal ni yuqoridan kessa → BUY
    MACD chiziq Signal ni pastdan kessa   → SELL
    """
    if len(closes) < MACD_SLOW + MACD_SIGNAL + 5:
        return {"signal": "NONE", "histogram": 0, "strength": 0}

    ema_fast   = calc_ema(closes, MACD_FAST)
    ema_slow   = calc_ema(closes, MACD_SLOW)
    macd_line  = ema_fast - ema_slow
    signal_line = calc_ema(macd_line[MACD_SLOW:], MACD_SIGNAL)

    # Signal line ni to'g'ri hizalash
    pad = len(macd_line) - len(signal_line)
    signal_padded = np.pad(signal_line, (pad, 0), constant_values=0)

    hist         = macd_line - signal_padded
    current_hist = hist[-1]
    prev_hist    = hist[-2]

    crossover  = prev_hist < 0 and current_hist >= 0
    crossunder = prev_hist > 0 and current_hist <= 0

    if crossover or current_hist > 0:
        signal   = "BUY"
        strength = min(abs(current_hist) / (abs(current_hist) + 0.001), 1.0)
    elif crossunder or current_hist < 0:
        signal   = "SELL"
        strength = min(abs(current_hist) / (abs(current_hist) + 0.001), 1.0)
    else:
        signal   = "NONE"
        strength = 0

    return {
        "signal": signal,
        "histogram": round(current_hist, 6),
        "crossover": crossover,
        "crossunder": crossunder,
        "strength": round(strength, 3)
    }


# ================================================================
#  4. STOCHASTIC OSCILLATOR
# ================================================================
def stochastic_signal(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> dict:
    """
    %K < 20 va %K > %D → BUY
    %K > 80 va %K < %D → SELL
    """
    if len(closes) < STOCH_K + STOCH_D + STOCH_SLOW + 5:
        return {"signal": "NONE", "k": 50, "d": 50, "strength": 0}

    k_values = []
    for i in range(STOCH_K - 1, len(closes)):
        h = np.max(highs[i - STOCH_K + 1:i + 1])
        l = np.min(lows[i - STOCH_K + 1:i + 1])
        if h == l:
            k_values.append(50)
        else:
            k_values.append((closes[i] - l) / (h - l) * 100)

    k_arr = np.array(k_values)

    # Slow %K
    slow_k = np.convolve(k_arr, np.ones(STOCH_SLOW) / STOCH_SLOW, mode='valid')
    # %D
    d_arr  = np.convolve(slow_k, np.ones(STOCH_D) / STOCH_D, mode='valid')

    if len(d_arr) < 2:
        return {"signal": "NONE", "k": 50, "d": 50, "strength": 0}

    k_cur = slow_k[-1]
    d_cur = d_arr[-1]
    k_prev = slow_k[-2]
    d_prev = d_arr[-2]

    if k_cur < 20 and k_prev <= d_prev and k_cur > d_cur:
        signal   = "BUY"
        strength = (20 - k_cur) / 20
    elif k_cur > 80 and k_prev >= d_prev and k_cur < d_cur:
        signal   = "SELL"
        strength = (k_cur - 80) / 20
    elif k_cur < 25:
        signal   = "BUY"
        strength = (25 - k_cur) / 25 * 0.5
    elif k_cur > 75:
        signal   = "SELL"
        strength = (k_cur - 75) / 25 * 0.5
    else:
        signal   = "NONE"
        strength = 0

    return {
        "signal": signal,
        "k": round(k_cur, 2),
        "d": round(d_cur, 2),
        "strength": round(min(strength, 1.0), 3)
    }


# ================================================================
#  5. BOLLINGER BANDS
# ================================================================
def bollinger_signal(closes: np.ndarray) -> dict:
    """
    Narx pastki band ostiga tushsa → BUY
    Narx yuqori band ustiga chiqsa → SELL
    """
    if len(closes) < BB_PERIOD + 5:
        return {"signal": "NONE", "position": 0, "strength": 0}

    sma   = np.mean(closes[-BB_PERIOD:])
    std   = np.std(closes[-BB_PERIOD:])
    upper = sma + BB_STD * std
    lower = sma - BB_STD * std
    price = closes[-1]

    band_width = upper - lower
    if band_width == 0:
        return {"signal": "NONE", "position": 0.5, "strength": 0}

    position = (price - lower) / band_width  # 0=pastki, 1=yuqori

    if price < lower:
        signal   = "BUY"
        strength = min((lower - price) / std, 1.0)
    elif price > upper:
        signal   = "SELL"
        strength = min((price - upper) / std, 1.0)
    elif position < 0.25:
        signal   = "BUY"
        strength = (0.25 - position) * 2
    elif position > 0.75:
        signal   = "SELL"
        strength = (position - 0.75) * 2
    else:
        signal   = "NONE"
        strength = 0

    return {
        "signal": signal,
        "upper": round(upper, 5),
        "middle": round(sma, 5),
        "lower": round(lower, 5),
        "position": round(position, 3),
        "strength": round(min(strength, 1.0), 3)
    }


# ================================================================
#  6. ATR — Average True Range (volatility)
# ================================================================
def calc_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
             period: int = ATR_PERIOD) -> float:
    if len(closes) < period + 2:
        return 1.0

    tr_list = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        tr_list.append(tr)

    tr_arr = np.array(tr_list)
    atr = np.mean(tr_arr[-period:])
    return round(atr, 5)


# ================================================================
#  7. SUPERTREND
# ================================================================
def supertrend_signal(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> dict:
    """
    Narx Supertrend ustida → BUY
    Narx Supertrend ostida → SELL
    """
    period = SUPERTREND_PERIOD
    mult   = SUPERTREND_MULT

    if len(closes) < period + 5:
        return {"signal": "NONE", "trend": 0, "strength": 0}

    atr_vals = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        atr_vals.append(tr)

    atr_arr = np.array(atr_vals)

    hl2 = (highs[1:] + lows[1:]) / 2
    upper_band = hl2 + mult * atr_arr
    lower_band = hl2 - mult * atr_arr

    supertrend = np.zeros(len(closes) - 1)
    direction  = np.zeros(len(closes) - 1)

    for i in range(period, len(supertrend)):
        atr_i = np.mean(atr_arr[max(0, i - period):i])
        ub = hl2[i] + mult * atr_i
        lb = hl2[i] - mult * atr_i

        if closes[i] > supertrend[i - 1]:
            supertrend[i] = lb
            direction[i]  = 1   # BUY
        else:
            supertrend[i] = ub
            direction[i]  = -1  # SELL

    current_dir = direction[-1]
    price = closes[-1]
    st    = supertrend[-1]

    if current_dir == 1:
        signal   = "BUY"
        strength = min((price - st) / price * 100, 1.0)
    elif current_dir == -1:
        signal   = "SELL"
        strength = min((st - price) / price * 100, 1.0)
    else:
        signal   = "NONE"
        strength = 0

    return {
        "signal": signal,
        "supertrend": round(st, 5),
        "direction": int(current_dir),
        "strength": round(abs(strength), 3)
    }


# ================================================================
#  8. OBV — On Balance Volume
# ================================================================
def obv_signal(closes: np.ndarray, volumes: np.ndarray) -> dict:
    """
    OBV o'sishi → BUY (hajm bilan tasdiqlangan)
    OBV kamayishi → SELL
    """
    if len(closes) < 20:
        return {"signal": "NONE", "trend": "FLAT", "strength": 0}

    obv = np.zeros(len(closes))
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv[i] = obv[i - 1] + volumes[i]
        elif closes[i] < closes[i - 1]:
            obv[i] = obv[i - 1] - volumes[i]
        else:
            obv[i] = obv[i - 1]

    # OBV EMA20
    obv_ema = calc_ema(obv, 20)
    current = obv[-1]
    ema_val = obv_ema[-1]

    if current > ema_val * 1.001:
        signal   = "BUY"
        strength = min((current - ema_val) / (abs(ema_val) + 1), 1.0)
    elif current < ema_val * 0.999:
        signal   = "SELL"
        strength = min((ema_val - current) / (abs(ema_val) + 1), 1.0)
    else:
        signal   = "NONE"
        strength = 0

    return {
        "signal": signal,
        "obv": round(current, 2),
        "obv_ema": round(ema_val, 2),
        "strength": round(min(abs(strength), 1.0), 3)
    }


# ================================================================
#  BARCHA SIGNALLARNI YIG'ISH
# ================================================================
def get_all_signals(highs, lows, closes, volumes) -> dict:
    """8 ta indikatorning barcha signallarini hisoblash"""
    h = np.array(highs, dtype=float)
    l = np.array(lows,  dtype=float)
    c = np.array(closes, dtype=float)
    v = np.array(volumes, dtype=float)

    signals = {
        "ema":        ema_signal(c),
        "rsi":        rsi_signal(c),
        "macd":       macd_signal(c),
        "stochastic": stochastic_signal(h, l, c),
        "bollinger":  bollinger_signal(c),
        "supertrend": supertrend_signal(h, l, c),
        "obv":        obv_signal(c, v),
    }

    atr = calc_atr(h, l, c)
    signals["atr"] = atr

    # Umumiy signal hisoblash
    buy_count  = sum(1 for k, v in signals.items() if isinstance(v, dict) and v.get("signal") == "BUY")
    sell_count = sum(1 for k, v in signals.items() if isinstance(v, dict) and v.get("signal") == "SELL")
    total      = buy_count + sell_count

    # Vazn bilan umumiy kuch hisoblash
    buy_strength  = sum(v.get("strength", 0) for k, v in signals.items()
                        if isinstance(v, dict) and v.get("signal") == "BUY")
    sell_strength = sum(v.get("strength", 0) for k, v in signals.items()
                        if isinstance(v, dict) and v.get("signal") == "SELL")

    signals["summary"] = {
        "buy_count":     buy_count,
        "sell_count":    sell_count,
        "buy_strength":  round(buy_strength, 3),
        "sell_strength": round(sell_strength, 3),
        "dominant":      "BUY" if buy_strength > sell_strength else ("SELL" if sell_strength > buy_strength else "NONE")
    }

    return signals
