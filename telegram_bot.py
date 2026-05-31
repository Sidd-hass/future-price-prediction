import time
import logging
import threading
import requests
from logger import (
    register_telegram_user, 
    unregister_telegram_user, 
    get_registered_users,
    get_bot_offset, 
    set_bot_offset
)

logger = logging.getLogger("telegram_bot")

def send_bot_message(bot_token: str, chat_id: str, text: str) -> bool:
    """
    Sends a simple message from the bot to a specific chat ID.
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to send bot message to {chat_id}: {e}")
        return False

def poll_updates(db_path: str, bot_token: str, stop_event: threading.Event = None):
    """
    Long-polls Telegram updates and handles /start, /stop, /status, /help commands.
    """
    logger.info("Entering Telegram bot updates polling loop...")
    
    # Try to load existing offset from DB
    offset = get_bot_offset(db_path)
    
    if offset is None:
        # Initialize offset by fetching the latest update
        try:
            url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
            resp = requests.get(url, params={"limit": 1, "timeout": 0}, timeout=10)
            resp.raise_for_status()
            updates = resp.json().get("result", [])
            if updates:
                offset = updates[0]["update_id"] + 1
                set_bot_offset(db_path, offset)
                logger.info(f"Initialized Telegram bot update offset to {offset}")
            else:
                logger.info("No existing Telegram updates found. Bot starting clean.")
        except Exception as e:
            logger.error(f"Error initializing Telegram bot offset: {e}")
            # If the API call failed, we'll try again in the loop with offset=None
    
    while not (stop_event and stop_event.is_set()):
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        params = {"timeout": 20}
        if offset is not None:
            params["offset"] = offset
            
        try:
            # We set timeout slightly larger than the API long-poll timeout
            resp = requests.get(url, params=params, timeout=25)
            resp.raise_for_status()
            resp_json = resp.json()
            
            if not resp_json.get("ok"):
                logger.error(f"Telegram getUpdates response not ok: {resp_json}")
                time.sleep(5)
                continue
                
            updates = resp_json.get("result", [])
            for update in updates:
                update_id = update.get("update_id")
                # Update offset immediately after we receive/process to avoid repeating on failures
                offset = update_id + 1
                set_bot_offset(db_path, offset)
                
                # Parse message details
                message = update.get("message", {})
                chat = message.get("chat", {})
                chat_id = chat.get("id")
                text = message.get("text", "").strip()
                
                if chat_id is not None and text:
                    chat_id_str = str(chat_id)
                    from_user = message.get("from", {})
                    username = from_user.get("username")
                    first_name = from_user.get("first_name")
                    last_name = from_user.get("last_name")
                    
                    if text.startswith("/start"):
                        register_telegram_user(db_path, chat_id_str, username, first_name, last_name)
                        send_bot_message(
                            bot_token, 
                            chat_id_str, 
                            "Welcome to Futures Discount Alert! 🚀\n\n"
                            "You are now registered to receive real-time discount and spread alerts.\n"
                            "To unsubscribe at any time, type /stop."
                        )
                        logger.info(f"Registered user {chat_id_str} (@{username}) via /start")
                        
                    elif text.startswith("/stop"):
                        unregister_telegram_user(db_path, chat_id_str)
                        send_bot_message(
                            bot_token, 
                            chat_id_str,
                            "You have been successfully unsubscribed from Futures Discount Alerts. 📴\n"
                            "Type /start if you wish to subscribe again in the future."
                        )
                        logger.info(f"Unregistered user {chat_id_str} (@{username}) via /stop")
                        
                    elif text.startswith("/status"):
                        registered_ids = get_registered_users(db_path)
                        if chat_id_str in registered_ids:
                            send_bot_message(
                                bot_token, 
                                chat_id_str,
                                "🟢 STATUS: Subscribed\n\n"
                                "You are active and will receive alerts when signal conditions are met."
                            )
                        else:
                            send_bot_message(
                                bot_token, 
                                chat_id_str,
                                "🔴 STATUS: Unsubscribed\n\n"
                                "You are not registered. Type /start to subscribe."
                            )
                            
                    elif text.startswith("/help"):
                        send_bot_message(
                            bot_token, 
                            chat_id_str,
                            "Available commands:\n"
                            "/start - Subscribe to alerts\n"
                            "/stop - Unsubscribe from alerts\n"
                            "/status - Check subscription status\n"
                            "/help - Show this help message"
                        )
                        
        except requests.RequestException as e:
            logger.warning(f"Error polling Telegram updates: {e}")
            # If the request fails, pause for a moment before retrying
            time.sleep(5)
        except Exception as e:
            logger.error(f"Unexpected error in Telegram polling loop: {e}", exc_info=True)
            time.sleep(5)

def start_telegram_bot_thread(db_path: str, bot_token: str):
    """
    Spins up the Telegram updates polling loop in a background daemon thread.
    Returns (thread, stop_event).
    """
    if not bot_token:
        logger.warning("Telegram Bot Token is empty. Bot listener thread will not be started.")
        return None, None
        
    stop_event = threading.Event()
    thread = threading.Thread(
        target=poll_updates,
        args=(db_path, bot_token, stop_event),
        daemon=True,
        name="TelegramBotPoller"
    )
    thread.start()
    logger.info("Started Telegram bot updates polling thread successfully.")
    return thread, stop_event
