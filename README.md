# 🤖 XAUUSD MT5 Avtomatik Savdo Boti

**MetaTrader 5** orqali **XAUUSD (Oltin/Dollar)** juftligida avtomatik savdo qiluvchi Python bot.

## ⚙️ Ishlash tartibi

```
10 BUY + 10 SELL ochiladi (0.01 lot)
        ↓
Har 3 soniyada jami foyda tekshiriladi
        ↓
Foyda ≥ $2 bo'lsa → barcha pozitsiyalar yopiladi
        ↓
Avtomatik yangi sikl boshlanadi ♻️
```

---

## 📁 Fayllar

```
avaz/
├── config.py       ← MT5 hisob ma'lumotlari va sozlamalar
├── mt5_trader.py   ← MT5 API moduli
├── bot.py          ← Asosiy bot mantiq
├── main.py         ← Ishga tushirish
├── requirements.txt
└── bot.log         ← Log (avtomatik)
```

---

## 🚀 O'rnatish

```bash
pip install -r requirements.txt
```

> ⚠️ MetaTrader5 kutubxonasi faqat **Windows** da ishlaydi!
> MT5 ilovasi kompyuterda o'rnatilgan va ishlab turishi kerak.

---

## ▶️ Ishga tushirish

```bash
python main.py
```

---

## ⚙️ Sozlamalar (config.py)

| Parametr | Qiymat | Tavsif |
|----------|--------|--------|
| `MT5_LOGIN` | 109947762 | Demo hisob login |
| `MT5_PASSWORD` | -tBfUb3j | Parol |
| `MT5_SERVER` | MetaQuotes-Demo | Server |
| `LOT` | 0.01 | Lot hajmi |
| `BUY_COUNT` | 10 | BUY soni |
| `SELL_COUNT` | 10 | SELL soni |
| `PROFIT_TARGET` | 2.0 | Foyda maqsadi ($) |
| `CHECK_INTERVAL` | 3 | Tekshirish oralig'i (soniya) |

---

## ⚠️ Ogohlantirishlar

- **Faqat Windows** da ishlaydi (MetaTrader5 Python kutubxonasi)
- MT5 ilovasi ochiq bo'lishi shart
- Demo hisob bilan sinab ko'ring
- `Ctrl+C` bosilsa barcha pozitsiyalar avtomatik yopiladi
