import json
import logging
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
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
    description_uz: str = ""


def load_regions() -> Dict[str, str]:
    with open(REGIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def translate_to_uzbek(text: str) -> str:
    if not text or len(text.strip()) < 5:
        return ""
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {"client": "gtx", "sl": "ko", "tl": "uz", "dt": "t", "q": text[:400]}
        resp = requests.get(url, params=params, timeout=8)
        if resp.status_code == 200:
            result = resp.json()
            return "".join(item[0] for item in result[0] if item[0]).strip()
    except Exception:
        pass
    return ""


def fetch_post_description(post_url: str) -> str:
    try:
        slug = post_url.rstrip("/").split("/")[-1]
        url = f"https://www.daangn.com/kr/cars/{slug}/?_data=routes%2Fkr.cars.%24carId"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            car = data.get("carPost", {})
            return (car.get("description") or car.get("content") or "").strip()
    except Exception:
        pass
    return ""


def fetch_region_posts(region_id: str, region_name: str) -> List[CarPost]:
    """Bitta region uchun ON_SALE postlarni olish."""
    in_param = urllib.parse.quote(f"{region_name}-{region_id}")
    url = f"{API_BASE}?in={in_param}&_data=routes%2Fkr.cars._index"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        
        # JSON parse xatosini oldini olish
        try:
            data = resp.json()
        except Exception:
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

    except Exception as e:
        logger.debug(f"Region {region_name}({region_id}): {e}")
        return []


def _parse_item(item: dict) -> Optional[CarPost]:
    post_id = item.get("id", "").strip("/").split("/")[-1]
    if not post_id:
        return None

    href = item.get("href", "")
    title = item.get("title", "Nomsiz")

    price_raw = item.get("price", 0)
    if price_raw:
        price = f"{price_raw:,}만원  ({price_raw * 10000:,} 원)"
    else:
        price = "Narx ko'rsatilmagan"

    car_data = item.get("carData", {})
    year = car_data.get("modelYear", 0)
    car_type = car_data.get("carType", "")

    drive_km = item.get("driveDistance", 0)
    mileage = f"{drive_km:,}km" if drive_km else ""

    region = item.get("region", {})
    location = region.get("name2") or region.get("name", "")

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
