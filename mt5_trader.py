# ============================================================
#  MT5 SAVDO MODULI — SL/TP BILAN
#  MetaTrader 5 bilan ishlash: ulanish, buy/sell SL/TP, yopish
# ============================================================

import MetaTrader5 as mt5
import logging
import time
from config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, SYMBOL, LOT, MAGIC

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
        logger.info(
            f"✅ MT5 ulandi | Hisob: {info.login} | "
            f"Balans: {info.balance:.2f} USD | Server: {info.server}"
        )

        # Symbol tekshirish
        sym = mt5.symbol_info(SYMBOL)
        if sym is None or not sym.visible:
            mt5.symbol_select(SYMBOL, True)
            time.sleep(0.5)

        return True

    def disconnect(self):
        mt5.shutdown()
        logger.info("MT5 ulanishi uzildi")

    # ----------------------------------------------------------
    #  FILLING MODE ANIQLASH
    # ----------------------------------------------------------
    def _get_filling(self) -> int:
        """
        Server qo'llab-quvvatlaydigan filling modeni avtomatik aniqlash
        MetaQuotes-Demo: RETURN ishlatadi
        """
        sym = mt5.symbol_info(SYMBOL)
        if sym is None:
            return mt5.ORDER_FILLING_RETURN

        fm = sym.filling_mode
        if fm & 4:   # RETURN — eng keng qo'llab-quvvatlanadigan
            return mt5.ORDER_FILLING_RETURN
        elif fm & 2: # IOC
            return mt5.ORDER_FILLING_IOC
        elif fm & 1: # FOK
            return mt5.ORDER_FILLING_FOK
        return mt5.ORDER_FILLING_RETURN

    # ----------------------------------------------------------
    #  ATR HISOBLASH (SL/TP uchun)
    # ----------------------------------------------------------
    def _calc_atr(self, period: int = 14) -> float:
        """H1 dan ATR hisoblash"""
        rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, period + 5)
        if rates is None or len(rates) < period:
            # Fallback: narxning 0.3%
            tick = mt5.symbol_info_tick(SYMBOL)
            return (tick.ask * 0.003) if tick else 10.0

        tr_list = [
            max(
                rates["high"][i] - rates["low"][i],
                abs(rates["high"][i] - rates["close"][i - 1]),
                abs(rates["low"][i]  - rates["close"][i - 1])
            )
            for i in range(1, len(rates))
        ]
        atr = sum(tr_list[-period:]) / period
        return round(atr, 5)

    # ----------------------------------------------------------
    #  SL / TP HISOBLASH
    # ----------------------------------------------------------
    def _calc_sl_tp(self, direction: str, price: float, atr: float) -> tuple:
        """
        ATR asosida SL va TP hisoblash
        BUY:  SL = price - ATR*1.5  |  TP = price + ATR*3.0
        SELL: SL = price + ATR*1.5  |  TP = price - ATR*3.0
        """
        sym  = mt5.symbol_info(SYMBOL)
        digs = sym.digits if sym else 2

        sl_dist = round(atr * 1.5, digs)
        tp_dist = round(atr * 3.0, digs)

        # Minimal masofa tekshirish
        if sym:
            min_dist = sym.trade_stops_level * sym.point
            sl_dist  = max(sl_dist, min_dist)
            tp_dist  = max(tp_dist, min_dist * 2)

        if direction == "buy":
            sl = round(price - sl_dist, digs)
            tp = round(price + tp_dist, digs)
        else:
            sl = round(price + sl_dist, digs)
            tp = round(price - tp_dist, digs)

        return sl, tp

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
    #  BUYURTMA OCHISH — SL/TP BILAN ✅
    # ----------------------------------------------------------
    def open_order(self, direction: str) -> dict | None:
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None:
            logger.error("Tick ma'lumoti yo'q")
            return None

        filling = self._get_filling()
        atr     = self._calc_atr()

        if direction == "buy":
            order_type = mt5.ORDER_TYPE_BUY
            price      = tick.ask
        else:
            order_type = mt5.ORDER_TYPE_SELL
            price      = tick.bid

        # SL va TP hisoblash
        sl, tp = self._calc_sl_tp(direction, price, atr)

        # SL/TP validatsiya
        if direction == "buy":
            if sl >= price or tp <= price:
                logger.error(f"❌ BUY SL/TP xato! price:{price} sl:{sl} tp:{tp}")
                return None
        else:
            if sl <= price or tp >= price:
                logger.error(f"❌ SELL SL/TP xato! price:{price} sl:{sl} tp:{tp}")
                return None

        request = {
            "action":       mt5.TRADE_ACTION_DEAL,
            "symbol":       SYMBOL,
            "volume":       float(LOT),
            "type":         order_type,
            "price":        price,
            "sl":           float(sl),
            "tp":           float(tp),
            "deviation":    50,
            "magic":        MAGIC,
            "comment":      f"bot_{direction}",
            "type_time":    mt5.ORDER_TIME_GTC,
            "type_filling": filling,
        }

        result = mt5.order_send(request)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            code = result.retcode if result else "None"
            logger.error(
                f"❌ {direction.upper()} xato | retcode: {code} | "
                f"{mt5.last_error()}"
            )
            # Filling xatosi bo'lsa RETURN bilan qayta urinish
            if result and result.retcode == 10030:
                request["type_filling"] = mt5.ORDER_FILLING_RETURN
                result = mt5.order_send(request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    return None
            else:
                return None

        logger.info(
            f"✅ {direction.upper()} ochildi | "
            f"ticket:{result.order} | narx:{price} | "
            f"SL:{sl} | TP:{tp} | ATR:{atr:.5f}"
        )
        return {
            "ticket":    result.order,
            "direction": direction,
            "price":     price,
            "sl":        sl,
            "tp":        tp,
            "atr":       atr
        }

    # ----------------------------------------------------------
    #  OCHIQ POZITSIYALAR
    # ----------------------------------------------------------
    def get_open_positions(self) -> list:
        positions = mt5.positions_get(symbol=SYMBOL)
        if positions is None:
            return []
        return [p for p in positions if p.magic == MAGIC]

    # ----------------------------------------------------------
    #  JAMI FOYDA HISOBLASH
    # ----------------------------------------------------------
    def get_total_profit(self) -> float:
        positions = self.get_open_positions()
        if not positions:
            return 0.0
        return round(sum(p.profit for p in positions), 4)

    # ----------------------------------------------------------
    #  BITTA POZITSIYANI YOPISH
    # ----------------------------------------------------------
    def close_position(self, position) -> bool:
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None:
            return False

        filling = self._get_filling()

        if position.type == mt5.ORDER_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price      = tick.bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price      = tick.ask

        request = {
            "action":       mt5.TRADE_ACTION_DEAL,
            "symbol":       SYMBOL,
            "volume":       position.volume,
            "type":         order_type,
            "position":     position.ticket,
            "price":        price,
            "deviation":    50,
            "magic":        MAGIC,
            "comment":      "bot_close",
            "type_time":    mt5.ORDER_TIME_GTC,
            "type_filling": filling,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            code = result.retcode if result else "None"
            logger.error(f"Yopishda xato | ticket:{position.ticket} | retcode:{code}")
            return False

        logger.info(
            f"✅ Yopildi | ticket:{position.ticket} | "
            f"foyda:{position.profit:.4f}$"
        )
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
