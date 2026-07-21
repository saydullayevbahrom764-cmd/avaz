# ============================================================
#  OANDA API KONFIGURATSIYA
#  Bu faylda API kalitlaringizni kiriting
# ============================================================

# OANDA API sozlamalari
# https://www.oanda.com/account/tpa/personal_token dan oling
OANDA_API_KEY = "YOUR_OANDA_API_KEY_HERE"

# Account ID: OANDA dashboard -> My Account -> Account ID
OANDA_ACCOUNT_ID = "YOUR_ACCOUNT_ID_HERE"

# Savdo muhiti: "practice" (demo) yoki "live" (real)
OANDA_ENVIRONMENT = "practice"   # Avval demo bilan sinang!

# API URL manzillar
API_URLS = {
    "practice": "https://api-fxpractice.oanda.com",
    "live":     "https://api-fxtrade.oanda.com"
}

# ============================================================
#  SAVDO SOZLAMALARI
# ============================================================

INSTRUMENT   = "XAU_USD"      # Oltin/Dollar
LOT_SIZE     = 0.01            # 0.01 lot = 1 oz (OANDA'da units bilan)
UNITS        = 1               # 0.01 lot ≈ 1 unit oltin (OANDA)

# Nechta pozitsiya ochilsin
BUY_COUNT    = 10              # 10 ta BUY
SELL_COUNT   = 10              # 10 ta SELL

# Necha dollar foydada yopilsin (jami barcha pozitsiyalar)
PROFIT_TARGET_USD = 2.0        # $2 foyda

# Tekshirish oralig'i (soniyada)
CHECK_INTERVAL = 5             # Har 5 soniyada foyda tekshiriladi

# Spread himoyasi (pipsda) - bu spread juda katta bo'lsa ochmaslik uchun
MAX_SPREAD_PIPS = 3.0

# Webhook server porti
WEBHOOK_PORT = 5000
WEBHOOK_SECRET = "my_secret_token_123"   # TradingView alertda shu tokenni yozing
