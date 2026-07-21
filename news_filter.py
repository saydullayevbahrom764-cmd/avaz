# ================================================================
#  NEWS_FILTER.PY — MUHIM YANGILIKLAR FILTRI
#  Economic calendar orqali yuqori ta'sirli yangiliklar tekshiriladi
#  Yangilikdan 30 daqiqa oldin va keyin savdo to'xtatiladi
# ================================================================

import urllib.request
import json
import logging
from datetime import datetime, timezone, timedelta
from config import NEWS_PAUSE_MINUTES, HIGH_IMPACT_ONLY

logger = logging.getLogger(__name__)

# ================================================================
#  OLDINDAN BELGILANGAN MUHIM YANGILIKLAR
#  (API ishlamasa ham ishlaydi)
# ================================================================

# Haftaning qaysi vaqtlarida muhim yangiliklar bo'lishi mumkin (UTC soat)
HIGH_RISK_HOURS = {
    # Dushanba
    0: [],
    # Seshanba
    1: [8, 9, 13, 14, 15],   # EUR, USD ma'lumotlari
    # Chorshanba
    2: [8, 9, 13, 14, 18],   # FOMC, USD
    # Payshanba
    3: [8, 9, 12, 13, 14],   # USD Unemployment, ECB
    # Juma
    4: [8, 9, 12, 13],       # NFP (Non-Farm Payrolls) — eng muhim!
    # Shanba
    5: [],
    # Yakshanba
    6: [],
}

# XAUUSD ga ta'sir qiluvchi muhim kalit so'zlar
GOLD_KEYWORDS = [
    "gold", "fed", "fomc", "interest rate", "inflation", "cpi",
    "nfp", "non-farm", "payroll", "gdp", "unemployment",
    "powell", "federal reserve", "monetary policy", "rate decision",
    "geopolit", "war", "conflict", "dollar", "usd"
]


# ================================================================
#  ECONOMIC CALENDAR API (ForexFactory)
# ================================================================

_news_cache    = []
_last_fetch    = None
_cache_minutes = 60   # 1 soat kesh


def fetch_news_calendar() -> list:
    """
    ForexFactory dan yangiliklar kalendarini olish.
    Agar ulanmasa — bo'sh ro'yxat qaytaradi (xavfsiz)
    """
    global _news_cache, _last_fetch

    now = datetime.now(timezone.utc)

    # Kesh tekshirish
    if _last_fetch and (now - _last_fetch).seconds < _cache_minutes * 60:
        return _news_cache

    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())

        news = []
        for item in data:
            try:
                impact = item.get("impact", "").lower()
                title  = item.get("title", "").lower()
                curr   = item.get("currency", "").upper()
                date_str = item.get("date", "")

                # Faqat USD va yuqori ta'sirli yangiliklar
                if HIGH_IMPACT_ONLY and impact not in ["high"]:
                    continue
                if curr not in ["USD", "XAU"]:
                    continue

                # Vaqtni parse qilish
                try:
                    event_time = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z")
                except:
                    continue

                news.append({
                    "title":   item.get("title", ""),
                    "time":    event_time,
                    "impact":  impact,
                    "currency": curr
                })
            except:
                continue

        _news_cache = news
        _last_fetch = now
        logger.info(f"📰 Yangiliklar yuklandi: {len(news)} ta muhim yangilik")
        return news

    except Exception as e:
        logger.warning(f"⚠️  Yangilik kalendarini yuklab bo'lmadi: {e}")
        logger.warning("    Bot hisob-kitob asosida davom etadi")
        _last_fetch = now
        _news_cache = []
        return []


# ================================================================
#  YANGILIK VAQTINI TEKSHIRISH
# ================================================================

def is_near_news(minutes_before: int = NEWS_PAUSE_MINUTES,
                 minutes_after: int  = NEWS_PAUSE_MINUTES) -> dict:
    """
    Hozir muhim yangilikka yaqin vaqtmi?
    Returns: {"blocked": bool, "reason": str, "minutes_left": int}
    """
    now  = datetime.now(timezone.utc)
    news = fetch_news_calendar()

    for item in news:
        event_time = item["time"]
        diff_seconds = (event_time - now).total_seconds()
        diff_minutes = diff_seconds / 60

        # Yangilikdan oldin
        if 0 < diff_minutes <= minutes_before:
            return {
                "blocked":      True,
                "reason":       f"Yangilik {diff_minutes:.0f} daqiqadan keyin: {item['title']}",
                "event":        item["title"],
                "minutes_left": int(diff_minutes),
                "event_time":   event_time.strftime("%H:%M UTC")
            }

        # Yangilikdan keyin
        if -minutes_after <= diff_minutes < 0:
            return {
                "blocked":      True,
                "reason":       f"Yangilik {abs(diff_minutes):.0f} daqiqa oldin bo'ldi: {item['title']}",
                "event":        item["title"],
                "minutes_left": int(minutes_after + diff_minutes),
                "event_time":   event_time.strftime("%H:%M UTC")
            }

    # API ishlamasa — vaqt asosida tekshirish
    weekday  = now.weekday()   # 0=Dushanba
    hour_utc = now.hour

    risky_hours = HIGH_RISK_HOURS.get(weekday, [])
    for risky_h in risky_hours:
        diff_h = abs(now.hour - risky_h) * 60 + now.minute
        if diff_h <= NEWS_PAUSE_MINUTES:
            return {
                "blocked":      True,
                "reason":       f"Potensial muhim yangilik vaqti: {risky_h}:00 UTC",
                "event":        "Potensial high-impact news",
                "minutes_left": NEWS_PAUSE_MINUTES - diff_h,
                "event_time":   f"{risky_h:02d}:00 UTC"
            }

    # Juma 12:30 UTC — NFP (eng muhim!)
    if weekday == 4 and hour_utc == 12 and now.minute >= 15 and now.minute <= 50:
        return {
            "blocked":      True,
            "reason":       "NFP (Non-Farm Payrolls) vaqti — eng xavfli!",
            "event":        "Non-Farm Payrolls",
            "minutes_left": 50 - now.minute,
            "event_time":   "12:30 UTC"
        }

    return {
        "blocked":      False,
        "reason":       "Xavfsiz — muhim yangilik yo'q",
        "event":        None,
        "minutes_left": 0,
        "event_time":   None
    }


# ================================================================
#  SPREAD TEKSHIRISH
# ================================================================

def check_spread(symbol_info) -> dict:
    """Spread juda katta emasligini tekshirish"""
    from config import MAX_SPREAD_POINTS

    if symbol_info is None:
        return {"ok": False, "spread": 0, "reason": "Symbol ma'lumoti yo'q"}

    spread = symbol_info.spread
    if spread > MAX_SPREAD_POINTS:
        return {
            "ok":     False,
            "spread": spread,
            "reason": f"Spread juda katta: {spread} points (max: {MAX_SPREAD_POINTS})"
        }

    return {"ok": True, "spread": spread, "reason": "Spread normal"}
