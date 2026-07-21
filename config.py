# ================================================================
#  PROFESSIONAL XAUUSD BOT — KONFIGURATSIYA
#  Kapital: $1000 | Maqsad: $20-50/kun | 24/7
# ================================================================

# ── MT5 HISOB ────────────────────────────────────────────────
MT5_LOGIN    = 109947762
MT5_PASSWORD = "-tBfUb3j"
MT5_SERVER   = "MetaQuotes-Demo"

# ── SAVDO ASOSLARI ───────────────────────────────────────────
SYMBOL       = "XAUUSD"
MAGIC        = 20250721        # Bot identifikatori

# ── KAPITAL VA RISK ──────────────────────────────────────────
BALANCE          = 1000.0      # Boshlang'ich kapital ($)
RISK_PER_TRADE   = 0.01        # Har savdoda risk: 1% = $10
MAX_DAILY_LOSS   = 0.03        # Kunlik max zarar: 3% = $30
DAILY_PROFIT_TARGET = 50.0     # Kunlik maqsad: $50

# ── LOT HISOBLASH ────────────────────────────────────────────
MIN_LOT      = 0.01
MAX_LOT      = 0.10
LOT_STEP     = 0.01

# ── SL / TP (ATR koeffitsientlari) ───────────────────────────
ATR_SL_MULT  = 1.5             # SL = ATR × 1.5
ATR_TP_MULT  = 3.0             # TP = ATR × 3.0  (1:2 risk:reward)
TRAILING_STEP = 0.5            # Trailing stop: ATR × 0.5

# ── INDIKATOR SOZLAMALARI ────────────────────────────────────
EMA_FAST     = 50
EMA_SLOW     = 200
RSI_PERIOD   = 14
RSI_OVERSOLD = 35
RSI_OVERBOUGHT = 65
STOCH_K      = 5
STOCH_D      = 3
STOCH_SLOW   = 3
MACD_FAST    = 12
MACD_SLOW    = 26
MACD_SIGNAL  = 9
BB_PERIOD    = 20
BB_STD       = 2.0
ATR_PERIOD   = 14
SUPERTREND_PERIOD = 10
SUPERTREND_MULT   = 3.0

# ── SIGNAL KUCHI ─────────────────────────────────────────────
# Nechta indikator bir yo'nalishda bo'lsa savdo ochiladi
MIN_SIGNALS  = 5               # Minimum 5/8 signal kerak

# ── TIMEFRAME VAZNLARI ───────────────────────────────────────
# Qaysi timeframe muhimroq
TF_WEIGHTS = {
    "M1":  0.10,               # 1 daqiqa  — kirish
    "H1":  0.30,               # 1 soat    — asosiy trend
    "D1":  0.35,               # 1 kun     — katta trend
    "W1":  0.25,               # 1 hafta   — global trend
}

# ── SESSIYA FILTRI ───────────────────────────────────────────
# London + New York — eng likvidli sessiyalar (UTC)
SESSIONS = [
    {"name": "London",   "start": 7,  "end": 16},
    {"name": "New York", "start": 12, "end": 21},
]
TRADE_ALL_SESSIONS = True      # True = 24/7, False = faqat sessiyalarda

# ── NEWS FILTER ──────────────────────────────────────────────
NEWS_PAUSE_MINUTES = 30        # Muhim yangilikdan 30 daqiqa oldin/keyin savdo yo'q
HIGH_IMPACT_ONLY   = True      # Faqat yuqori ta'sirli yangiliklar

# ── TEKSHIRISH ORALIG'I ──────────────────────────────────────
CHECK_INTERVAL     = 5         # Har 5 soniyada signal tekshirish
CANDLE_WAIT        = True      # Yangi sham ochilganda tahlil

# ── MAX OCHIQ POZITSIYALAR ───────────────────────────────────
MAX_POSITIONS      = 3         # Bir vaqtda max 3 ta pozitsiya

# ── SPREAD FILTRI ────────────────────────────────────────────
MAX_SPREAD_POINTS  = 50        # Max spread (XAUUSD uchun points)
