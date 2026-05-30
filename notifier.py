import requests
from datetime import datetime
import pytz

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
        f"Basis:   {basis:.2f}%  ✅ [Threshold > 2.00%]\n"
        f"Spread:  {spread:.2f}% ✅ [Threshold 0.00%-0.20%]\n\n"
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
