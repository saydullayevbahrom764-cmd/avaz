import json
import logging
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timezone

import requests

from config import REQUEST_DELAY, MIN_DATE

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

# 차량 설명 (mashina tavsifi) olish uchun detail endpoint
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
    description: str = ""          # Koreyscha tavsif
    description_uz: str = ""       # O'zbekcha tarjima


def load_regions() -> Dict[str, str]:
    """regions.json dan barcha region ID va nomlarni yuklash."""
    with open(REGIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def is_after_min_date(published_at: str) -> bool:
    """
    Post MIN_DATE (2026-07-21) dan keyin e'lon qilinganmi?
    published_at format: "2026-07-21T06:00:00.278Z"
    """
    if not published_at:
        return False
    try:
        # ISO format parse
        post_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        min_date = datetime.fromisoformat(MIN_DATE + "T00:00:00+00:00")
        return post_date >= min_date
    except Exception:
        return False


def translate_to_uzbek(text: str) -> str:
    """
    Koreyscha matnni o'zbekchaga Google Translate orqali tarjima qilish.
    Bepul, API key shart emas.
    """
    if not text or len(text.strip()) < 5:
        return ""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "ko",        # Manba: Koreyscha
            "tl": "uz",        # Maqsad: O'zbekcha
            "dt": "t",
            "q": text[:500],   # Max 500 belgi
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
    """
    Post detail sahifasidan 차량 설명 (mashina tavsifi) olish.
    """
    try:
        # Detail API endpoint
        slug = post_url.rstrip("/").split("/")[-1]
        detail_url = f"https://www.daangn.com/kr/cars/{slug}/?_data=routes%2Fkr.cars.%24carId"
        
        resp = requests.get(detail_url, headers=DETAIL_HEADERS, timeout=10)
        if resp.status_code != 200:
            return ""
        
        data = resp.json()
        
        # Turli joylarda tavsif bo'lishi mumkin
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
    """
    Bitta region uchun ON_SALE va MIN_DATE dan keyingi postlarni olish.
    """
    in_param = urllib.parse.quote(f"{region_name}-{region_id}")
    url = (
        f"{API_BASE}?in={in_param}"
        f"&_data=routes%2Fkr.cars._index"
    )

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
        # Faqat sotuvdagi postlar
        if item.get("status") != "ON_SALE":
            continue

        # Faqat MIN_DATE dan keyingi postlar
        published_at = item.get("publishedAt", "")
        if not is_after_min_date(published_at):
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
        price_won = price_raw * 10000  # 만원 → 원 ga aylantirish
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
