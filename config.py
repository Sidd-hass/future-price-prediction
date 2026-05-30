import os
from dotenv import load_dotenv

# Load variables from .env file if it exists
load_dotenv()

UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN", "")
UPSTOX_CLIENT_ID = os.getenv("UPSTOX_CLIENT_ID", "")
UPSTOX_CLIENT_SECRET = os.getenv("UPSTOX_CLIENT_SECRET", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Numeric configurations
try:
    BASIS_THRESHOLD = float(os.getenv("BASIS_THRESHOLD", 2.0))
except ValueError:
    BASIS_THRESHOLD = 2.0

try:
    SPREAD_MIN = float(os.getenv("SPREAD_MIN", 0.0))
except ValueError:
    SPREAD_MIN = 0.0

try:
    SPREAD_MAX = float(os.getenv("SPREAD_MAX", 0.2))
except ValueError:
    SPREAD_MAX = 0.2

try:
    BREACH_COUNT_THRESHOLD = int(os.getenv("BREACH_COUNT_THRESHOLD", 5))
except ValueError:
    BREACH_COUNT_THRESHOLD = 5

try:
    COOLDOWN_MINUTES = int(os.getenv("COOLDOWN_MINUTES", 15))
except ValueError:
    COOLDOWN_MINUTES = 15

# Watchlist symbol extraction
watchlist_raw = os.getenv("WATCHLIST", "")
if watchlist_raw:
    WATCHLIST = [sym.strip().upper() for sym in watchlist_raw.split(",") if sym.strip()]
else:
    WATCHLIST = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
