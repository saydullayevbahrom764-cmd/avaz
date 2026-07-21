import asyncio
import logging
import time
from datetime import datetime

from telegram import Bot, InputMediaPhoto
from telegram.error import TelegramError
from telegram.constants import ParseMode

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHANNEL_ID,
    CHECK_INTERVAL,
    CONCURRENT_REGIONS,
)
from db import (
    init_db,
    is_seen,
    mark_seen,
    mark_seen_batch,
    get_seen_count,
    save_checkpoint,
    load_checkpoint,
)
from scraper import load_regions, fetch_region_posts, CarPost

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

CAR_TYPE_MAP = {
    "SUV": "🚙 SUV",
    "MIDDLE": "🚗 Sedan/Hatchback",
    "BIG": "🚐 Katta",
    "SMALL": "🚘 Kichik",
    "TRUCK": "🚚 Yuk mashinasi",
    "BUS": "🚌 Avtobus",
    "VAN": "🚐 Van/Minivan",
    "SPORTS": "🏎 Sport",
    "EV": "⚡ Elektr",
}


def format_message(post: CarPost) -> str:
    lines = [f"🚗 <b>{post.title}</b>", ""]

    if post.price:
        lines.append(f"💰 <b>Narx:</b> {post.price}")
    if post.year:
        lines.append(f"📅 <b>Yil:</b> {post.year}")
    if post.mileage:
        lines.append(f"🛣 <b>Yurish:</b> {post.mileage}")
    if post.car_type:
        label = CAR_TYPE_MAP.get(post.car_type, post.car_type)
        lines.append(f"🏷 <b>Turi:</b> {label}")
    if post.location:
        lines.append(f"📍 <b>Joylashuv:</b> {post.location} (Koreya)")

    lines += ["", f'🔗 <a href="{post.post_url}">Daangn\'da ko\'rish →</a>']
    return "\n".join(lines)


async def send_post(bot: Bot, post: CarPost) -> bool:
    text = format_message(post)
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
        # Rasm yuklanmasa matn sifatida yuborish
        if post.image_url:
            try:
                await bot.send_message(
                    chat_id=TELEGRAM_CHANNEL_ID,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=False,
                )
                return True
            except TelegramError:
                pass
        logger.error(f"Yuborishda xato [{post.id}]: {e}")
        return False


async def process_region(
    bot: Bot,
    region_id: str,
    region_name: str,
    semaphore: asyncio.Semaphore,
) -> int:
    """
    Bitta regionni tekshirish va yangi postlarni yuborish.
    Semaphore orqali parallel so'rovlar soni cheklanadi.
    """
    async with semaphore:
        loop = asyncio.get_event_loop()
        # Scraping — sinxron, thread pool orqali
        posts = await loop.run_in_executor(
            None, fetch_region_posts, region_id, region_name
        )

        sent = 0
        for post in posts:
            if is_seen(post.id):
                continue

            success = await send_post(bot, post)
            if success:
                mark_seen(post.id, post.title, post.price, post.location, post.post_url)
                sent += 1
                logger.info(
                    f"✅ {post.location} | {post.title} | {post.price}"
                )
                # Flood limit himoyasi
                await asyncio.sleep(2)

        return sent


async def run_full_scan(bot: Bot, regions: dict) -> int:
    """
    Barcha 3847 ta regionni parallel ravishda skanerlash.
    CONCURRENT_REGIONS ta region bir vaqtda tekshiriladi.
    """
    semaphore = asyncio.Semaphore(CONCURRENT_REGIONS)
    region_list = list(regions.items())
    total = len(region_list)
    total_sent = 0

    logger.info(f"Skan boshlandi: {total} ta region, {CONCURRENT_REGIONS} parallel")
    start_time = time.time()

    # Barcha regionlarni task sifatida yaratish
    tasks = [
        process_region(bot, rid, rname, semaphore)
        for rid, rname in region_list
    ]

    # Natijalarni yig'ish (xatolar bo'lsa ham davom etadi)
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if isinstance(r, int):
            total_sent += r

    elapsed = time.time() - start_time
    logger.info(
        f"Skan tugadi: {total_sent} ta yangi post | "
        f"Vaqt: {elapsed:.0f}s | "
        f"Jami ko'rilgan: {get_seen_count()}"
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

    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    try:
        me = await bot.get_me()
        logger.info(f"Bot ulandi: @{me.username}")
    except TelegramError as e:
        logger.error(f"Bot ulanishda xato: {e}")
        return

    # Barcha regionlarni yuklash
    regions = load_regions()
    logger.info(f"Yuklandi: {len(regions)} ta region (butun Koreya)")
    logger.info(f"Kanal: {TELEGRAM_CHANNEL_ID}")
    logger.info(f"Parallel: {CONCURRENT_REGIONS} ta region bir vaqtda")

    # Birinchi skan
    await run_full_scan(bot, regions)

    # Asosiy sikl — har CHECK_INTERVAL sekundda yangi skan
    while True:
        logger.info(f"{CHECK_INTERVAL} sekunddan keyin yangi skan...")
        await asyncio.sleep(CHECK_INTERVAL)
        await run_full_scan(bot, regions)


if __name__ == "__main__":
    asyncio.run(main())
