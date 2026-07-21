# 🚗 Daangn Car Bot

[daangn.com/kr/car/](https://www.daangn.com/kr/car/) saytidagi yangi mashina e'lonlarini avtomatik ravishda Telegram kanalga yuboruvchi bot.

## Xususiyatlari

- ✅ Yangi e'lonlarni avtomatik aniqlash
- ✅ Rasm + narx + joylashuv + yil + yurish masofasi
- ✅ Takrorlanmaslik (SQLite orqali ko'rilganlar saqlanadi)
- ✅ Sozlanuvchi tekshirish intervali
- ✅ Rasm yuklanmasa matn sifatida fallback

---

## O'rnatish

### 1. Talablar

- Python 3.9+
- pip

### 2. Loyihani yuklab olish

```bash
git clone <repo-url>
cd daangn-car-bot
```

### 3. Kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Telegram Bot yaratish

1. Telegramda [@BotFather](https://t.me/BotFather) ga yozing
2. `/newbot` buyrug'ini yuboring
3. Bot nomini kiriting
4. Olingan **TOKEN** ni saqlang

### 5. Kanal sozlash

1. Telegram kanalini yarating (yoki mavjud kanaldan foydalaning)
2. Botni kanalga **Admin** sifatida qo'shing
3. Kanal username ini saqlang (masalan: `@mening_kanalim`)

### 6. `.env` fayl yaratish

```bash
cp .env.example .env
```

`.env` faylni tahrirlang:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCDEFghijklmnopqrstuvwxyz
TELEGRAM_CHANNEL_ID=@mening_kanalim
CHECK_INTERVAL=300
DB_PATH=seen_posts.db
```

| Parametr | Tavsif | Default |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather dan olingan token | **Majburiy** |
| `TELEGRAM_CHANNEL_ID` | Kanal username (`@...`) yoki ID (`-100...`) | **Majburiy** |
| `CHECK_INTERVAL` | Tekshirish oralig'i (sekund) | `300` (5 daqiqa) |
| `DB_PATH` | SQLite fayl nomi | `seen_posts.db` |

---

## Ishga tushirish

```bash
python bot.py
```

### Natija

```
2024-01-01 10:00:00 [INFO] Bot ulandi: @mening_botim
2024-01-01 10:00:00 [INFO] Bot ishga tushdi. Har 300 sekundda tekshiriladi.
2024-01-01 10:00:00 [INFO] Yangi postlar tekshirilmoqda...
2024-01-01 10:00:05 [INFO] Yuborildi: [abc123] 2020 현대 소나타 | 1,500만원
2024-01-01 10:00:07 [INFO] ✅ 3 ta yangi post yuborildi
```

---

## Faqat scraperni sinab ko'rish

```bash
python scraper.py
```

---

## Server (VPS) da doimiy ishlatish

### systemd service (Linux)

```bash
sudo nano /etc/systemd/system/daangn-bot.service
```

```ini
[Unit]
Description=Daangn Car Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/daangn-car-bot
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable daangn-bot
sudo systemctl start daangn-bot
sudo systemctl status daangn-bot
```

### yoki screen bilan

```bash
screen -S daangn-bot
python bot.py
# Ctrl+A, D — screendan chiqish
```

---

## Fayl strukturasi

```
daangn-car-bot/
├── bot.py          # Asosiy bot (Telegram yuborish, sikl)
├── scraper.py      # Playwright bilan saytdan ma'lumot olish
├── db.py           # SQLite — ko'rilgan postlarni saqlash
├── config.py       # Sozlamalar (.env dan o'qiydi)
├── .env            # Shaxsiy sozlamalar (git ga qo'shilmaydi!)
├── .env.example    # Namuna
├── requirements.txt
└── seen_posts.db   # Avtomatik yaratiladi
```

---

## Muammolar

| Muammo | Yechim |
|---|---|
| `playwright install` xatosi | `playwright install-deps chromium` ham bajaring |
| Bot kanalga yoza olmaydi | Botni kanal admini qilib qo'shganingizni tekshiring |
| Postlar topilmaydi | Daangn sayt strukturasi o'zgargan bo'lishi mumkin, `scraper.py` selector larni yangilang |
| `404` yoki `403` xatosi | User-agent o'zgartiring yoki proxy ishlating |
