# ============================================================
#  WEBHOOK SERVER
#  TradingView alertlarini qabul qilish va botni boshqarish
# ============================================================

from flask import Flask, request, jsonify
import threading
import logging
from oanda_trader import OandaTrader
from config import WEBHOOK_PORT, WEBHOOK_SECRET

logger = logging.getLogger(__name__)

app = Flask(__name__)
trader = OandaTrader()

# Bot holati (thread-safe)
bot_status = {
    "running": False,
    "cycle": 0,
    "total_profit": 0.0
}
bot_lock = threading.Lock()


# ============================================================
#  YORDAMCHI: TOKEN TEKSHIRISH
# ============================================================

def verify_token(data: dict) -> bool:
    """TradingView alertdan kelgan tokenni tekshirish"""
    token = data.get("token", "")
    if token != WEBHOOK_SECRET:
        logger.warning(f"⚠️  Noto'g'ri token: {token}")
        return False
    return True


# ============================================================
#  ENDPOINT: /webhook  — TradingView signali
# ============================================================

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    TradingView alert quyidagi JSON formatda yuboradi:
    {
        "token": "my_secret_token_123",
        "action": "buy" | "sell" | "close_all" | "start" | "stop",
        "comment": "optional"
    }
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"status": "error", "message": "Bo'sh JSON"}), 400

        logger.info(f"📩 Webhook qabul qilindi: {data}")

        # Token tekshirish
        if not verify_token(data):
            return jsonify({"status": "error", "message": "Noto'g'ri token"}), 403

        action = data.get("action", "").lower()

        # --- START: botni ishga tushirish ---
        if action == "start":
            with bot_lock:
                if bot_status["running"]:
                    return jsonify({"status": "ok", "message": "Bot allaqachon ishlayapti"}), 200
                bot_status["running"] = True

            t = threading.Thread(target=run_bot_thread, daemon=True)
            t.start()
            logger.info("🚀 Bot webhook orqali ishga tushirildi")
            return jsonify({"status": "ok", "message": "Bot ishga tushdi"}), 200

        # --- STOP: botni to'xtatish ---
        elif action == "stop":
            with bot_lock:
                bot_status["running"] = False
            trader.close_all_trades()
            logger.info("🛑 Bot webhook orqali to'xtatildi")
            return jsonify({"status": "ok", "message": "Bot to'xtatildi, pozitsiyalar yopildi"}), 200

        # --- CLOSE_ALL: barcha pozitsiyalarni yopish ---
        elif action == "close_all":
            closed = trader.close_all_trades()
            logger.info(f"🔒 {closed} ta pozitsiya yopildi (webhook)")
            return jsonify({"status": "ok", "message": f"{closed} ta pozitsiya yopildi"}), 200

        # --- BUY: bitta buy ochish ---
        elif action == "buy":
            trade = trader.open_order("buy", label="webhook_buy")
            if trade:
                return jsonify({"status": "ok", "trade_id": trade["trade_id"], "price": trade["price"]}), 200
            return jsonify({"status": "error", "message": "BUY ochishda xato"}), 500

        # --- SELL: bitta sell ochish ---
        elif action == "sell":
            trade = trader.open_order("sell", label="webhook_sell")
            if trade:
                return jsonify({"status": "ok", "trade_id": trade["trade_id"], "price": trade["price"]}), 200
            return jsonify({"status": "error", "message": "SELL ochishda xato"}), 500

        # --- STATUS: bot holati ---
        elif action == "status":
            counts = trader.count_open_trades()
            pnl = trader.get_total_unrealized_pnl()
            with bot_lock:
                running = bot_status["running"]
                cycle = bot_status["cycle"]
                total_profit = bot_status["total_profit"]
            return jsonify({
                "status": "ok",
                "bot_running": running,
                "cycle": cycle,
                "total_profit": total_profit,
                "open_trades": counts,
                "unrealized_pnl": pnl
            }), 200

        else:
            logger.warning(f"Noma'lum action: {action}")
            return jsonify({"status": "error", "message": f"Noma'lum action: {action}"}), 400

    except Exception as e:
        logger.error(f"Webhook xato: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================
#  ENDPOINT: /health  — Server sog'lig'ini tekshirish
# ============================================================

@app.route("/health", methods=["GET"])
def health():
    counts = trader.count_open_trades()
    pnl = trader.get_total_unrealized_pnl()
    with bot_lock:
        status = bot_status.copy()
    return jsonify({
        "status": "ok",
        "bot": status,
        "open_trades": counts,
        "unrealized_pnl": pnl
    }), 200


# ============================================================
#  BOT THREAD FUNKSIYASI
# ============================================================

def run_bot_thread():
    """Alohida thread da botni ishga tushirish"""
    import time
    from bot import open_all_positions, wait_for_profit_and_close, check_spread
    from config import BUY_COUNT, SELL_COUNT

    logger.info("🤖 Bot thread ishga tushdi")

    while True:
        with bot_lock:
            if not bot_status["running"]:
                logger.info("🛑 Bot thread to'xtatildi")
                break
            bot_status["cycle"] += 1
            cycle_num = bot_status["cycle"]

        logger.info(f"\n📊 SIKL #{cycle_num} (thread)")

        # Spread tekshirish
        spread_ok = False
        while not spread_ok:
            with bot_lock:
                if not bot_status["running"]:
                    return
            spread_ok = check_spread(trader)
            if not spread_ok:
                time.sleep(10)

        # Pozitsiyalar ochish
        opened = open_all_positions(trader)
        if len(opened) < (BUY_COUNT + SELL_COUNT) * 0.5:
            logger.error("Yetarli pozitsiya ochilmadi, 30s kutilmoqda...")
            trader.close_all_trades()
            time.sleep(30)
            continue

        # Foyda kutish
        profit = wait_for_profit_and_close(trader)

        with bot_lock:
            bot_status["total_profit"] += profit

        logger.info(f"✅ Sikl #{cycle_num} tugadi | Foyda: ${profit:.4f}")
        time.sleep(3)


# ============================================================
#  SERVERNI ISHGA TUSHIRISH
# ============================================================

def start_webhook_server():
    logger.info(f"🌐 Webhook server ishga tushmoqda: http://0.0.0.0:{WEBHOOK_PORT}")
    logger.info(f"   Endpoints:")
    logger.info(f"   POST /webhook  — TradingView signali")
    logger.info(f"   GET  /health   — Server holati")
    app.run(host="0.0.0.0", port=WEBHOOK_PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    start_webhook_server()
