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
from db import (
    init_db,
    is_seen,
    mark_seen,
    mark_seen_no_send,
    get_seen_count,
)
from scraper import (
    load_regions,
    fetch_region_posts,
    fetch_post_description,
    translate_to_uzbek,
    set_bot_start_time,
    is_new_post,
    CarPost,
)

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

# Birinchi skan tugadimi?
FIRST_SCAN_DONE = False


def format_date(published_at: str) -> str:
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


def format_message(post: CarPost) -> str:
    """Telegram uchun xabar formatlash."""
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
    if post.published_at:
        lines.append(f"🕐 <b>E'lon sanasi:</b> {format_date(post.published_at)}")

    # O'zbekcha tavsif
    if post.description_uz:
        lines.append("")
        lines.append(f"📝 <b>Tavsif:</b>")
        lines.append(f"{post.description_uz}")
        lines.append(f"<i>⚠️ Tarjima avtomatik — xatolik bo'lishi mumkin</i>")

    # Link — har doim ko'rinadi
    lines += ["", f'🔗 <a href="{post.post_url}">Daangn\'da ko\'rish →</a>']
    return "\n".join(lines)


async def enrich_post(post: CarPost) -> CarPost:
    """Tavsif olish va o'zbekchaga tarjima."""
    loop = asyncio.get_event_loop()
    description = await loop.run_in_executor(
        None, fetch_post_description, post.post_url
    )
    if description:
        post.description = description
        post.description_uz = await loop.run_in_executor(
            None, translate_to_uzbek, description
        )
    return post


async def send_post(bot: Bot, post: CarPost) -> bool:
    """Bitta postni Telegram kanalga yuborish."""
    text = format_message(post)

    # Telegram caption max 1024 belgi
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
    first_scan: bool = False,
) -> int:
    """Bitta regionni tekshirish."""
    async with semaphore:
        loop = asyncio.get_event_loop()
        posts = await loop.run_in_executor(
            None, fetch_region_posts, region_id, region_name
        )

        sent = 0
        for post in posts:
            # Avval ko'rilganmi?
            if is_seen(post.id):
                continue

            if first_scan:
                # Birinchi skanda — hamma postni ko'rilgan deb belgilaymiz
                # lekin YUBORMAYMIZ
                mark_seen_no_send(post.id, post.title, post.price, post.location, post.post_url)
            else:
                # Keyingi skanlar — faqat yangi postlarni yuboramiz
                if not is_new_post(post.published_at):
                    # Eski post — ko'rilgan deb belgilaymiz, yubormaymiz
                    mark_seen_no_send(post.id, post.title, post.price, post.location, post.post_url)
                    continue

                # Yangi post — tavsif olib yuboramiz
                post = await enrich_post(post)
                success = await send_post(bot, post)
                if success:
                    mark_seen(post.id, post.title, post.price, post.location, post.post_url)
                    sent += 1
                    logger.info(f"✅ {post.location} | {post.title} | {post.price}")
                    await asyncio.sleep(2)

        return sent


async def run_scan(bot: Bot, regions: dict, first_scan: bool = False) -> int:
    """Barcha regionlarni skanerlash."""
    global FIRST_SCAN_DONE

    semaphore = asyncio.Semaphore(CONCURRENT_REGIONS)
    region_list = list(regions.items())
    total = len(region_list)
    total_sent = 0

    if first_scan:
        logger.info(f"BIRINCHI SKAN: {total} ta region — postlar saqlanadi, yuborilmaydi")
    else:
        logger.info(f"Yangi postlar tekshirilmoqda: {total} ta region")

    start_time = time.time()

    tasks = [
        process_region(bot, rid, rname, semaphore, first_scan)
        for rid, rname in region_list
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if isinstance(r, int):
            total_sent += r

    elapsed = time.time() - start_time

    if first_scan:
        logger.info(
            f"Birinchi skan tugadi | "
            f"Saqlangan: {get_seen_count()} ta post | "
            f"Vaqt: {elapsed:.0f}s"
        )
        logger.info("Endi yangi postlar kuzatiladi ✅")
    else:
        logger.info(
            f"Skan tugadi: {total_sent} ta yangi post | "
            f"Vaqt: {elapsed:.0f}s | "
            f"Jami ko'rilgan: {get_seen_count()}"
        )

    return total_sent


async def main():
    global FIRST_SCAN_DONE

    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN topilmadi!")
        return
    if not TELEGRAM_CHANNEL_ID:
        logger.error("TELEGRAM_CHANNEL_ID topilmadi!")
        return

    init_db()

    # Bot start vaqtini belgilash
    set_bot_start_time()

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
    FIRST_SCAN_DONE = True

    # Asosiy sikl — yangi postlarni kuzatish
    while True:
        logger.info(f"{CHECK_INTERVAL} sekunddan keyin yangi postlar tekshiriladi...")
        await asyncio.sleep(CHECK_INTERVAL)
        await run_scan(bot, regions, first_scan=False)


if __name__ == "__main__":
    asyncio.run(main())
