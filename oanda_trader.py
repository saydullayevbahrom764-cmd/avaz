# ============================================================
#  OANDA SAVDO MODULI
#  Buy/Sell ochish, pozitsiyalarni boshqarish, foyda hisoblash
# ============================================================

import requests
import json
import logging
from datetime import datetime
from config import (
    OANDA_API_KEY, OANDA_ACCOUNT_ID, OANDA_ENVIRONMENT,
    API_URLS, INSTRUMENT, UNITS
)

# Logging sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class OandaTrader:
    """OANDA API bilan ishlash uchun asosiy klass"""

    def __init__(self):
        self.base_url = API_URLS[OANDA_ENVIRONMENT]
        self.headers = {
            "Authorization": f"Bearer {OANDA_API_KEY}",
            "Content-Type": "application/json"
        }
        self.account_id = OANDA_ACCOUNT_ID
        logger.info(f"OandaTrader ishga tushdi | Muhit: {OANDA_ENVIRONMENT.upper()}")

    # ----------------------------------------------------------
    #  HISOBNI TEKSHIRISH
    # ----------------------------------------------------------
    def get_account_info(self):
        """Hisob ma'lumotlarini olish"""
        url = f"{self.base_url}/v3/accounts/{self.account_id}"
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            r.raise_for_status()
            data = r.json()["account"]
            logger.info(f"Hisob: {data['id']} | Balans: {data['balance']} USD | NAV: {data['NAV']}")
            return data
        except Exception as e:
            logger.error(f"Hisob ma'lumotlari olishda xato: {e}")
            return None

    # ----------------------------------------------------------
    #  NARX OLISH
    # ----------------------------------------------------------
    def get_price(self):
        """Joriy bid/ask narxini olish"""
        url = f"{self.base_url}/v3/accounts/{self.account_id}/pricing"
        params = {"instruments": INSTRUMENT}
        try:
            r = requests.get(url, headers=self.headers, params=params, timeout=10)
            r.raise_for_status()
            prices = r.json()["prices"][0]
            bid = float(prices["bids"][0]["price"])
            ask = float(prices["asks"][0]["price"])
            spread = round(ask - bid, 5)
            logger.debug(f"Narx | BID: {bid} | ASK: {ask} | Spread: {spread}")
            return {"bid": bid, "ask": ask, "spread": spread}
        except Exception as e:
            logger.error(f"Narx olishda xato: {e}")
            return None

    # ----------------------------------------------------------
    #  BUYURTMA OCHISH
    # ----------------------------------------------------------
    def open_order(self, direction: str, units: int = UNITS, label: str = ""):
        """
        Buyurtma ochish
        direction: 'buy' yoki 'sell'
        units: miqdor (0.01 lot = 1 unit XAUUSD uchun)
        """
        if direction.lower() == "buy":
            order_units = abs(units)
        elif direction.lower() == "sell":
            order_units = -abs(units)
        else:
            logger.error(f"Noto'g'ri yo'nalish: {direction}")
            return None

        url = f"{self.base_url}/v3/accounts/{self.account_id}/orders"
        body = {
            "order": {
                "type": "MARKET",
                "instrument": INSTRUMENT,
                "units": str(order_units),
                "timeInForce": "FOK",
                "positionFill": "DEFAULT",
                "clientExtensions": {
                    "comment": label or f"bot_{direction}_{datetime.now().strftime('%H%M%S')}"
                }
            }
        }

        try:
            r = requests.post(url, headers=self.headers, json=body, timeout=10)
            r.raise_for_status()
            data = r.json()

            if "orderFillTransaction" in data:
                fill = data["orderFillTransaction"]
                trade_id = fill["tradeOpened"]["tradeID"]
                price = fill["price"]
                logger.info(f"✅ {direction.upper()} ochildi | ID: {trade_id} | Narx: {price} | Label: {label}")
                return {
                    "trade_id": trade_id,
                    "direction": direction,
                    "price": float(price),
                    "units": order_units,
                    "label": label
                }
            else:
                logger.warning(f"Buyurtma to'ldirilmadi: {data}")
                return None

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP xato: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Buyurtma ochishda xato: {e}")
            return None

    # ----------------------------------------------------------
    #  OCHIQ POZITSIYALARNI OLISH
    # ----------------------------------------------------------
    def get_open_trades(self):
        """Barcha ochiq pozitsiyalarni olish"""
        url = f"{self.base_url}/v3/accounts/{self.account_id}/trades"
        params = {"instrument": INSTRUMENT, "state": "OPEN"}
        try:
            r = requests.get(url, headers=self.headers, params=params, timeout=10)
            r.raise_for_status()
            trades = r.json().get("trades", [])
            logger.debug(f"Ochiq pozitsiyalar soni: {len(trades)}")
            return trades
        except Exception as e:
            logger.error(f"Pozitsiyalar olishda xato: {e}")
            return []

    # ----------------------------------------------------------
    #  JAMI FOYDA/ZARAR HISOBLASH
    # ----------------------------------------------------------
    def get_total_unrealized_pnl(self):
        """Barcha ochiq pozitsiyalarning jami foyda/zarari (USD)"""
        trades = self.get_open_trades()
        if not trades:
            return 0.0

        total_pnl = 0.0
        for trade in trades:
            unrealized = float(trade.get("unrealizedPL", 0))
            total_pnl += unrealized

        logger.info(f"Jami foyda/zarar: {total_pnl:.4f} USD | Pozitsiyalar: {len(trades)}")
        return round(total_pnl, 4)

    # ----------------------------------------------------------
    #  BITTA POZITSIYANI YOPISH
    # ----------------------------------------------------------
    def close_trade(self, trade_id: str):
        """Berilgan ID bo'yicha pozitsiyani yopish"""
        url = f"{self.base_url}/v3/accounts/{self.account_id}/trades/{trade_id}/close"
        try:
            r = requests.put(url, headers=self.headers, timeout=10)
            r.raise_for_status()
            data = r.json()
            if "orderFillTransaction" in data:
                fill = data["orderFillTransaction"]
                realized = fill.get("pl", "0")
                logger.info(f"✅ Pozitsiya yopildi | ID: {trade_id} | Foyda: {realized} USD")
                return True
            return False
        except Exception as e:
            logger.error(f"Pozitsiya yopishda xato (ID: {trade_id}): {e}")
            return False

    # ----------------------------------------------------------
    #  BARCHA POZITSIYALARNI YOPISH
    # ----------------------------------------------------------
    def close_all_trades(self):
        """Barcha ochiq XAUUSD pozitsiyalarini yopish"""
        trades = self.get_open_trades()
        if not trades:
            logger.info("Yopiladigan pozitsiya yo'q")
            return 0

        closed = 0
        for trade in trades:
            trade_id = trade["id"]
            if self.close_trade(trade_id):
                closed += 1

        logger.info(f"Jami {closed}/{len(trades)} pozitsiya yopildi")
        return closed

    # ----------------------------------------------------------
    #  POZITSIYALAR SONI HISOBLASH
    # ----------------------------------------------------------
    def count_open_trades(self):
        """Ochiq buy va sell pozitsiyalar sonini qaytarish"""
        trades = self.get_open_trades()
        buy_count = 0
        sell_count = 0

        for trade in trades:
            units = float(trade.get("currentUnits", 0))
            if units > 0:
                buy_count += 1
            elif units < 0:
                sell_count += 1

        return {"buy": buy_count, "sell": sell_count, "total": len(trades)}
