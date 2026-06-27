import config
import logging
from logger import get_registered_users
from notifier import broadcast_telegram

logging.basicConfig(level=logging.INFO)

def run_test():
    db_path = "alerts.db" # The default used in your app
    
    # Get all registered users (including the channel)
    chat_ids = get_registered_users(db_path)
    
    if not chat_ids:
        print("No users or channels registered yet! Send /start to the bot first.")
        return

    print(f"Sending test alert to {len(chat_ids)} registered chat(s)...")
    
    # Send a fake test alert
    broadcast_telegram(
        bot_token=config.TELEGRAM_BOT_TOKEN,
        chat_ids=chat_ids,
        db_path=db_path,
        symbol="TEST_RELIANCE",
        spot=2500.0,
        cur_fut=2450.0,
        nxt_fut=2400.0,
        basis=-2.0,
        spread=-2.04,
        cur_expiry="2026-06-30",
        nxt_expiry="2026-07-28"
    )
    print("Test alert sent successfully! Check your Telegram channel.")

if __name__ == "__main__":
    run_test()
