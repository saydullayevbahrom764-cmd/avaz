import asyncio
import logging
import time
from datetime import datetime, timezone

from telegram import Bot
from telegram.error import TelegramError
from telegram.constants import ParseMode
from telegram.request import HTTPXRequest

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHANNEL_ID,
    CHECK_INTERVAL,
    CONCURRENT_REGIONS,
)
from db import init_db, is_seen, mark_seen, mark_seen_no_send, get_seen_count
from scraper import (
    load_regions,
    fetch_region_posts,
    fetch_post_description,
    translate_to_uzbek,
    CarPost,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Bot ishga tushgan vaqt
BOT_START_TIME: datetime = None

CAR_TYPE_MAP = {
    "SUV": "🚙 SUV",
    "MIDDLE": "🚗 Sedan",
    "BIG": "🚐 Katta",
    "SMALL": "🚘 Kichik",
    "TRUCK": "🚚 Yuk",
    "BUS": "🚌 Avtobus",
    "VAN": "🚐 Van",
    "SPORTS": "🏎 Sport",
    "EV": "⚡ Elektr",
}


def format_date(published_at: str) -> str:
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def format_message(post: CarPost) -> str:
    lines = [f"🚗 <b>{post.title}</b>", ""]

    if post.price:
        lines.append(f"💰 <b>Narx:</b> {post.price}")
    if post.year:
        lines.append(f"📅 <b>Yil:</b> {post.year}")
    if post.mileage:
        lines.append(f"🛣 <b>Yurish:</b> {post.mileage}")
    if post.car_type:
        lines.append(f"🏷 <b>Turi:</b> {CAR_TYPE_MAP.get(post.car_type, post.car_type)}")
    if post.location:
        lines.append(f"📍 <b>Joylashuv:</b> {post.location} (Koreya)")
    if post.published_at:
        lines.append(f"🕐 <b>E'lon:</b> {format_date(post.published_at)}")
    if post.description_uz:
        lines.append(f"\n📝 <b>Tavsif:</b>\n{post.description_uz}")
        lines.append(f"<i>⚠️ Tarjima avtomatik</i>")

    lines.append(f'\n🔗 <a href="{post.post_url}">Daangn\'da ko\'rish →</a>')
    return "\n".join(lines)


async def enrich_post(post: CarPost) -> CarPost:
    loop = asyncio.get_event_loop()
    desc = await loop.run_in_executor(None, fetch_post_description, post.post_url)
    if desc:
        post.description_uz = await loop.run_in_executor(None, translate_to_uzbek, desc)
    return post


async def send_post(bot: Bot, post: CarPost) -> bool:
    text = format_message(post)
    if len(text) > 1024:
        text = text[:1020] + "..."

    try:
        if post.image_url:
            await bot.send_photo(
                chat_id=TELEGRAM_CHANNEL_ID,
                photo=post.image_url,
                caption=text,
                parse_mode=ParseMode.HTML,
            )
        else:
            await bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False,
            )
        return True
    except TelegramError as e:
        try:
            await bot.send_message(
                chat_id=TELEGRAM_CHANNEL_ID,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False,
            )
            return True
        except TelegramError:
            logger.error(f"Yuborishda xato [{post.id}]: {e}")
            return False


def is_new_post(published_at: str) -> bool:
    """Bot ishga tushganidan keyin qo'yilgan post."""
    if not published_at or BOT_START_TIME is None:
        return False
    try:
        post_date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return post_date >= BOT_START_TIME
    except Exception:
        return False


async def process_region(
    bot: Bot,
    region_id: str,
    region_name: str,
    semaphore: asyncio.Semaphore,
    first_scan: bool,
) -> int:
    async with semaphore:
        loop = asyncio.get_event_loop()
        posts = await loop.run_in_executor(
            None, fetch_region_posts, region_id, region_name
        )

        sent = 0
        for post in posts:
            if is_seen(post.id):
                continue

            if first_scan:
                # 1-skan: faqat DB ga saqla, yuborma
                mark_seen_no_send(
                    post.id, post.title, post.price, post.location, post.post_url
                )
            else:
                # Keyingi skanlar: faqat bot ishga tushganidan keyin qo'yilgan
                if not is_new_post(post.published_at):
                    mark_seen_no_send(
                        post.id, post.title, post.price, post.location, post.post_url
                    )
                    continue

                # Yangi post — yuborish
                post = await enrich_post(post)
                if await send_post(bot, post):
                    mark_seen(
                        post.id, post.title, post.price, post.location, post.post_url
                    )
                    sent += 1
                    logger.info(f"✅ {post.location} | {post.title} | {post.price}")
                    await asyncio.sleep(2)

        return sent


async def run_scan(bot: Bot, regions: dict, first_scan: bool = False) -> int:
    global BOT_START_TIME

    semaphore = asyncio.Semaphore(CONCURRENT_REGIONS)
    region_list = list(regions.items())
    total_sent = 0
    start = time.time()

    if first_scan:
        logger.info(f"1-SKAN: {len(region_list)} ta region — mavjud postlar saqlanadi")
    else:
        logger.info(f"Yangi postlar tekshirilmoqda: {len(region_list)} ta region")

    tasks = [
        process_region(bot, rid, rname, semaphore, first_scan)
        for rid, rname in region_list
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if isinstance(r, int):
            total_sent += r

    elapsed = time.time() - start

    if first_scan:
        logger.info(
            f"1-skan tugadi | DB: {get_seen_count()} ta post | {elapsed:.0f}s"
        )
        # Bot start vaqtini 1-skan tugagandan keyin belgilash
        BOT_START_TIME = datetime.now(timezone.utc)
        logger.info(f"Yangi postlar kuzatiladi — start: {BOT_START_TIME.strftime('%Y-%m-%d %H:%M:%S')} UTC ✅")
    else:
        logger.info(
            f"Skan: {total_sent} ta yangi post | {elapsed:.0f}s | Jami: {get_seen_count()}"
        )

    return total_sent


async def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN topilmadi!")
        return
    if not TELEGRAM_CHANNEL_ID:
        logger.error("TELEGRAM_CHANNEL_ID topilmadi!")
        return

    init_db()

    request = HTTPXRequest(
        connection_pool_size=20,
        read_timeout=30,
        write_timeout=30,
        connect_timeout=30,
        pool_timeout=60,
    )
    bot = Bot(token=TELEGRAM_BOT_TOKEN, request=request)

    try:
        me = await bot.get_me()
        logger.info(f"Bot ulandi: @{me.username}")
    except TelegramError as e:
        logger.error(f"Bot ulanishda xato: {e}")
        return

    regions = load_regions()
    logger.info(f"Yuklandi: {len(regions)} ta region (butun Koreya)")
    logger.info(f"Kanal: {TELEGRAM_CHANNEL_ID}")

    # 1-skan: mavjud postlarni saqlash (yubormasdan)
    await run_scan(bot, regions, first_scan=True)

    # Asosiy sikl
    while True:
        logger.info(f"{CHECK_INTERVAL}s kutilmoqda...")
        await asyncio.sleep(CHECK_INTERVAL)
        await run_scan(bot, regions, first_scan=False)


if __name__ == "__main__":
    asyncio.run(main())
