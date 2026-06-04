import requests
import config
import logging
from datetime import datetime
import pytz
from logger import unregister_telegram_user

logger = logging.getLogger("notifier")

def send_telegram(bot_token: str, chat_id: str, symbol: str, spot: float, 
                  cur_fut: float, nxt_fut: float, basis: float, spread: float, 
                  cur_expiry: str, nxt_expiry: str):
    """
    Sends a formatted Telegram message to the specified chat.
    """
    ist = pytz.timezone('Asia/Kolkata')
    timestamp = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")
    
    message = (
        "🚨 FUTURES DISCOUNT ALERT\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Stock:          {symbol}\n"
        f"Time:           {timestamp} IST\n\n"
        f"Spot Price:     ₹{spot}\n"
        f"Cur Month Fut:  ₹{cur_fut}  ({basis:.2f}% discount)  Exp: {cur_expiry}\n"
        f"Nxt Month Fut:  ₹{nxt_fut}  ({spread:.2f}% vs cur)   Exp: {nxt_expiry}\n\n"
        f"Basis:   {basis:.2f}%  ✅ [Threshold > {config.BASIS_THRESHOLD:.2f}%]\n"
        f"Spread:  {spread:.2f}% ✅ [Threshold {config.SPREAD_MIN:.2f}% - {config.SPREAD_MAX:.2f}%]\n\n"
        "SIGNAL: BOTH CONDITIONS MET"
    )
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    return response

def broadcast_telegram(bot_token: str, chat_ids: list, db_path: str, symbol: str, spot: float,
                       cur_fut: float, nxt_fut: float, basis: float, spread: float,
                       cur_expiry: str, nxt_expiry: str):
    """
    Sends a formatted Telegram message to all registered chats in chat_ids.
    If sending fails with 403 Forbidden (bot blocked) or 400 (chat not found / invalid),
    it automatically removes the chat_id from the database.
    """
    success_count = 0
    failed_count = 0
    
    for chat_id in chat_ids:
        try:
            send_telegram(
                bot_token=bot_token,
                chat_id=chat_id,
                symbol=symbol,
                spot=spot,
                cur_fut=cur_fut,
                nxt_fut=nxt_fut,
                basis=basis,
                spread=spread,
                cur_expiry=cur_expiry,
                nxt_expiry=nxt_expiry
            )
            success_count += 1
        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            try:
                resp_body = e.response.json() if e.response is not None else {}
            except Exception:
                resp_body = {}
            description = resp_body.get("description", "")
            
            # 403 = Forbidden (e.g. user blocked the bot)
            # 400 = Bad Request (e.g. chat not found / invalid chat ID)
            if status_code == 403 or (status_code == 400 and "chat not found" in description.lower()):
                logger.warning(f"Removing subscriber {chat_id} (Reason: {description or 'Blocked/Invalid chat'})")
                try:
                    unregister_telegram_user(db_path, chat_id)
                except Exception as db_err:
                    logger.error(f"Failed to unregister blocked user {chat_id} from DB: {db_err}")
            else:
                logger.error(f"HTTP error sending alert to {chat_id}: {e}")
            failed_count += 1
        except Exception as e:
            logger.error(f"Unexpected error sending alert to {chat_id}: {e}")
            failed_count += 1
            
    logger.info(f"Broadcast alert completed: {success_count} succeeded, {failed_count} failed.")
