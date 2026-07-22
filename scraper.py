import json
import logging
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timezone

import requests

from config import REQUEST_DELAY

logger = logging.getLogger(__name__)

API_BASE = "https://www.daangn.com/kr/cars/"
REGIONS_FILE = Path(__file__).parent / "regions.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.daangn.com/",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

DETAIL_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.daangn.com/",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# Bot ishga tushgan vaqt — shu vaqtdan oldingi postlar yuborilmaydi
BOT_START_TIME: Optional[datetime] = None


def set_bot_start_time():
    """Bot ishga tushgan vaqtni belgilash."""
    global BOT_START_TIME
    BOT_START_TIME = datetime.now(timezone.utc)
    logger.info(f"Bot start vaqti: {BOT_START_TIME.strftime('%Y-%m-%d %H:%M:%S')} UTC")


def is_new_post(published_at: str) -> bool:
    """
    Post bot ishga tushganidan keyin e'lon qilinganmi?
    Birinchi skanda barcha mavjud postlar DB ga saqlanadi (yuborilmaydi),
    keyingi skanlardan yangilari yuboriladi.
    """
    if not published_at:
        return False
    try:
        post_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        if BOT_START_TIME is None:
            return True
        return post_date >= BOT_START_TIME
    except Exception:
        return False


@dataclass
class CarPost:
    id: str
    title: str
    price: str
    year: int
    mileage: str
    location: str
    image_url: str
    post_url: str
    car_type: str = ""
    status: str = ""
    published_at: str = ""
    description: str = ""
    description_uz: str = ""


def load_regions() -> Dict[str, str]:
    """regions.json dan barcha region ID va nomlarni yuklash."""
    with open(REGIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def translate_to_uzbek(text: str) -> str:
    """Koreyscha matnni o'zbekchaga Google Translate orqali tarjima."""
    if not text or len(text.strip()) < 5:
        return ""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "ko",
            "tl": "uz",
            "dt": "t",
            "q": text[:500],
        }
        resp = requests.get(url, params=params, timeout=8)
        if resp.status_code == 200:
            result = resp.json()
            translated = ""
            for item in result[0]:
                if item[0]:
                    translated += item[0]
            return translated.strip()
    except Exception as e:
        logger.debug(f"Tarjima xatosi: {e}")
    return ""


def fetch_post_description(post_url: str) -> str:
    """Post detail sahifasidan 차량 설명 olish."""
    try:
        slug = post_url.rstrip("/").split("/")[-1]
        detail_url = f"https://www.daangn.com/kr/cars/{slug}/?_data=routes%2Fkr.cars.%24carId"
        resp = requests.get(detail_url, headers=DETAIL_HEADERS, timeout=10)
        if resp.status_code != 200:
            return ""
        data = resp.json()
        car_post = data.get("carPost", {})
        description = (
            car_post.get("description", "") or
            car_post.get("content", "") or
            data.get("description", "") or
            ""
        )
        return description.strip()
    except Exception as e:
        logger.debug(f"Tavsif olishda xato: {e}")
        return ""


def fetch_region_posts(region_id: str, region_name: str) -> List[CarPost]:
    """Bitta region uchun ON_SALE postlarni olish."""
    in_param = urllib.parse.quote(f"{region_name}-{region_id}")
    url = f"{API_BASE}?in={in_param}&_data=routes%2Fkr.cars._index"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception as e:
        logger.debug(f"Region {region_name}({region_id}) xato: {e}")
        return []

    raw_posts = data.get("carAllPage", {}).get("carPosts", [])
    posts = []

    for item in raw_posts:
        if item.get("status") != "ON_SALE":
            continue
        post = _parse_item(item)
        if post:
            posts.append(post)

    return posts


def _parse_item(item: dict) -> Optional[CarPost]:
    """JSON itemdan CarPost yaratish."""
    post_id = item.get("id", "").strip("/").split("/")[-1]
    if not post_id:
        return None

    href = item.get("href", "")
    title = item.get("title", "Nomsiz")

    price_raw = item.get("price", 0)
    if price_raw:
        price_won = price_raw * 10000
        price = f"{price_raw:,}만원  ({price_won:,} 원)"
    else:
        price = "Narx ko'rsatilmagan"

    car_data = item.get("carData", {})
    year = car_data.get("modelYear", 0)
    car_type = car_data.get("carType", "")

    drive_km = item.get("driveDistance", 0)
    mileage = f"{drive_km:,}km" if drive_km else ""

    region = item.get("region", {})
    location = region.get("name2", "") or region.get("name", "")

    images = item.get("images", [])
    image_url = images[0] if images else ""

    return CarPost(
        id=post_id,
        title=title,
        price=price,
        year=year,
        mileage=mileage,
        location=location,
        image_url=image_url,
        post_url=href,
        car_type=car_type,
        status=item.get("status", ""),
        published_at=item.get("publishedAt", ""),
    )
