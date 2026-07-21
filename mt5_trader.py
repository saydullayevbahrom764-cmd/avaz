# ============================================================
#  MT5 SAVDO MODULI
#  MetaTrader 5 bilan ishlash: ulanish, buy/sell, yopish
# ============================================================

import MetaTrader5 as mt5
import logging
import time
from config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, SYMBOL, LOT, MAGIC

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MT5Trader:

    # ----------------------------------------------------------
    #  ULANISH
    # ----------------------------------------------------------
    def connect(self) -> bool:
        if not mt5.initialize():
            logger.error(f"MT5 initialize xato: {mt5.last_error()}")
            return False

        ok = mt5.login(
            login=MT5_LOGIN,
            password=MT5_PASSWORD,
            server=MT5_SERVER
        )
        if not ok:
            logger.error(f"MT5 login xato: {mt5.last_error()}")
            mt5.shutdown()
            return False

        info = mt5.account_info()
        logger.info(f"✅ MT5 ulandi | Hisob: {info.login} | Balans: {info.balance} USD | Server: {info.server}")
        return True

    def disconnect(self):
        mt5.shutdown()
        logger.info("MT5 ulanishi uzildi")

    # ----------------------------------------------------------
    #  NARX OLISH
    # ----------------------------------------------------------
    def get_price(self):
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None:
            logger.error(f"Narx olinmadi: {mt5.last_error()}")
            return None
        return {"bid": tick.bid, "ask": tick.ask, "spread": round(tick.ask - tick.bid, 5)}

    # ----------------------------------------------------------
    #  BUYURTMA OCHISH
    # ----------------------------------------------------------
    def open_order(self, direction: str) -> dict | None:
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None:
            logger.error("Tick ma'lumoti yo'q")
            return None

        sym = mt5.symbol_info(SYMBOL)
        if sym is None or not sym.visible:
            mt5.symbol_select(SYMBOL, True)
            time.sleep(0.5)

        if direction == "buy":
            order_type = mt5.ORDER_TYPE_BUY
            price      = tick.ask
        else:
            order_type = mt5.ORDER_TYPE_SELL
            price      = tick.bid

        request = {
            "action":    mt5.TRADE_ACTION_DEAL,
            "symbol":    SYMBOL,
            "volume":    LOT,
            "type":      order_type,
            "price":     price,
            "deviation": 20,
            "magic":     MAGIC,
            "comment":   f"bot_{direction}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            code = result.retcode if result else "None"
            logger.error(f"❌ {direction.upper()} xato | retcode: {code} | {mt5.last_error()}")
            return None

        logger.info(f"✅ {direction.upper()} ochildi | ticket: {result.order} | narx: {price}")
        return {"ticket": result.order, "direction": direction, "price": price}

    # ----------------------------------------------------------
    #  OCHIQ POZITSIYALAR
    # ----------------------------------------------------------
    def get_open_positions(self) -> list:
        positions = mt5.positions_get(symbol=SYMBOL)
        if positions is None:
            return []
        # Faqat shu bot ochganlarini qaytarish
        return [p for p in positions if p.magic == MAGIC]

    # ----------------------------------------------------------
    #  JAMI FOYDA HISOBLASH
    # ----------------------------------------------------------
    def get_total_profit(self) -> float:
        positions = self.get_open_positions()
        if not positions:
            return 0.0
        total = sum(p.profit for p in positions)
        return round(total, 4)

    # ----------------------------------------------------------
    #  BITTA POZITSIYANI YOPISH
    # ----------------------------------------------------------
    def close_position(self, position) -> bool:
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None:
            return False

        if position.type == mt5.ORDER_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price      = tick.bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price      = tick.ask

        request = {
            "action":    mt5.TRADE_ACTION_DEAL,
            "symbol":    SYMBOL,
            "volume":    position.volume,
            "type":      order_type,
            "position":  position.ticket,
            "price":     price,
            "deviation": 20,
            "magic":     MAGIC,
            "comment":   "bot_close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            code = result.retcode if result else "None"
            logger.error(f"Yopishda xato | ticket: {position.ticket} | retcode: {code}")
            return False

        logger.info(f"✅ Yopildi | ticket: {position.ticket} | foyda: {position.profit:.4f}$")
        return True

    # ----------------------------------------------------------
    #  BARCHA POZITSIYALARNI YOPISH
    # ----------------------------------------------------------
    def close_all(self) -> int:
        positions = self.get_open_positions()
        if not positions:
            logger.info("Yopiladigan pozitsiya yo'q")
            return 0
        closed = 0
        for pos in positions:
            if self.close_position(pos):
                closed += 1
            time.sleep(0.2)
        logger.info(f"Jami {closed}/{len(positions)} pozitsiya yopildi")
        return closed

    # ----------------------------------------------------------
    #  POZITSIYALAR SONI
    # ----------------------------------------------------------
    def count_positions(self) -> dict:
        positions = self.get_open_positions()
        buy  = sum(1 for p in positions if p.type == mt5.ORDER_TYPE_BUY)
        sell = sum(1 for p in positions if p.type == mt5.ORDER_TYPE_SELL)
        return {"buy": buy, "sell": sell, "total": len(positions)}
