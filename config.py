# ============================================================
#  GRID TRADING BOT - KONFIGURATSIYA
# ============================================================

# MT5 hisob ma'lumotlari
MT5_LOGIN    = 109947762
MT5_PASSWORD = "-tBfUb3j"
MT5_SERVER   = "MetaQuotes-Demo"

# Savdo sozlamalari
SYMBOL         = "XAUUSD"
LOT            = 0.01          # Har bir pozitsiya uchun lot
MAGIC          = 77777         # Grid bot identifikatori

# Grid sozlamalari
GRID_STEP      = 20            # Har bir grid oralig'i (point)
BUY_COUNT      = 6             # BUY pozitsiyalar soni
SELL_COUNT     = 6             # SELL pozitsiyalar soni

# Foyda/Zarar chegaralari
PROFIT_TARGET  = 5.0           # $5 foydada hammasi yopiladi
MAX_LOSS       = -1.5          # -$1.5 bo'lsa ham davom etadi (faqat log)

# Tekshirish oralig'i
CHECK_INTERVAL = 2             # Har 2 soniyada tekshirish
