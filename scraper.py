import json
import logging
import time
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict

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


def load_regions() -> Dict[str, str]:
    """regions.json dan barcha region ID va nomlarni yuklash."""
    with open(REGIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)  # {id: name, ...}


def fetch_region_posts(region_id: str, region_name: str) -> List[CarPost]:
    """
    Bitta region uchun ON_SALE postlarni olish.
    URL format: /kr/cars/?in=지역명-ID&_data=...
    """
    in_param = urllib.parse.quote(f"{region_name}-{region_id}")
    url = (
        f"{API_BASE}?in={in_param}"
        f"&_data=routes%2Fkr.cars._index"
    )

    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            logger.debug(f"Region {region_name}({region_id}): HTTP {resp.status_code}")
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


def _parse_item(item: dict):
    """JSON itemdan CarPost yaratish."""
    post_id = item.get("id", "").strip("/").split("/")[-1]
    if not post_id:
        return None

    href = item.get("href", "")
    title = item.get("title", "Nomsiz")

    price_raw = item.get("price", 0)
    price = f"{price_raw:,}만원" if price_raw else "Narx ko'rsatilmagan"

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


def fetch_all_regions_posts(
    regions: Dict[str, str],
    start_index: int = 0,
    progress_callback=None,
) -> List[CarPost]:
    """
    Barcha regionlarni ketma-ket aylanib, yangi postlarni yig'ish.
    start_index: oxirgi to'xtagan joydan davom etish uchun.
    """
    all_posts = []
    region_list = list(regions.items())  # [(id, name), ...]
    total = len(region_list)

    for i in range(start_index, total):
        region_id, region_name = region_list[i]

        posts = fetch_region_posts(region_id, region_name)
        if posts:
            all_posts.extend(posts)
            logger.debug(
                f"[{i+1}/{total}] {region_name}: {len(posts)} ta post"
            )

        if progress_callback:
            progress_callback(i, total)

        time.sleep(REQUEST_DELAY)

    return all_posts
