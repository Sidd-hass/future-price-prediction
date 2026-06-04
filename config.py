import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load variables from .env file if it exists
load_dotenv()

# Path to the conditions JSON file
_conditions_path = Path(__file__).parent / "conditions.json"

# ──────────────────────────────────────────────
# Helper conversion functions
# ──────────────────────────────────────────────
def _to_float(val, default):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default

def _to_int(val, default):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default

# ──────────────────────────────────────────────
# 1. Start with .env / environment variable defaults
# ──────────────────────────────────────────────
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN", "")
UPSTOX_CLIENT_ID = os.getenv("UPSTOX_CLIENT_ID", "")
UPSTOX_CLIENT_SECRET = os.getenv("UPSTOX_CLIENT_SECRET", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

BASIS_THRESHOLD = _to_float(os.getenv("BASIS_THRESHOLD"), 2.0)
SPREAD_MIN = _to_float(os.getenv("SPREAD_MIN"), 0.0)
SPREAD_MAX = _to_float(os.getenv("SPREAD_MAX"), 0.2)
BREACH_COUNT_THRESHOLD = _to_int(os.getenv("BREACH_COUNT_THRESHOLD"), 5)
COOLDOWN_MINUTES = _to_int(os.getenv("COOLDOWN_MINUTES"), 15)

_watchlist_raw = os.getenv("WATCHLIST", "")
if _watchlist_raw:
    WATCHLIST = [sym.strip().upper() for sym in _watchlist_raw.split(",") if sym.strip()]
else:
    WATCHLIST = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]

# ──────────────────────────────────────────────
# 2. Override with conditions.json if it exists
#    (JSON values take priority over .env)
# ──────────────────────────────────────────────
if _conditions_path.is_file():
    try:
        with open(_conditions_path, "r", encoding="utf-8") as f:
            _cfg = json.load(f)

        # Upstox credentials (nested under "upstox")
        _upstox = _cfg.get("upstox", {})
        if _upstox.get("UPSTOX_CLIENT_ID"):
            UPSTOX_CLIENT_ID = _upstox["UPSTOX_CLIENT_ID"]
        elif _upstox.get("client_id"):
            UPSTOX_CLIENT_ID = _upstox["client_id"]

        if _upstox.get("UPSTOX_CLIENT_SECRET"):
            UPSTOX_CLIENT_SECRET = _upstox["UPSTOX_CLIENT_SECRET"]
        elif _upstox.get("client_secret"):
            UPSTOX_CLIENT_SECRET = _upstox["client_secret"]

        # Telegram credentials (nested under "telegram")
        _tg = _cfg.get("telegram", {})
        if _tg.get("TELEGRAM_BOT_TOKEN"):
            TELEGRAM_BOT_TOKEN = _tg["TELEGRAM_BOT_TOKEN"]
        elif _tg.get("bot_token"):
            TELEGRAM_BOT_TOKEN = _tg["bot_token"]

        if _tg.get("TELEGRAM_CHAT_ID"):
            TELEGRAM_CHAT_ID = str(_tg["TELEGRAM_CHAT_ID"])
        elif _tg.get("chat_id"):
            TELEGRAM_CHAT_ID = str(_tg["chat_id"])

        # Thresholds (nested under "thresholds")
        _thr = _cfg.get("thresholds", {})
        if "basis_threshold" in _thr:
            BASIS_THRESHOLD = _to_float(_thr["basis_threshold"], BASIS_THRESHOLD)
        if "spread_min" in _thr:
            SPREAD_MIN = _to_float(_thr["spread_min"], SPREAD_MIN)
        if "spread_max" in _thr:
            SPREAD_MAX = _to_float(_thr["spread_max"], SPREAD_MAX)
        if "breach_count_threshold" in _thr:
            BREACH_COUNT_THRESHOLD = _to_int(_thr["breach_count_threshold"], BREACH_COUNT_THRESHOLD)
        if "cooldown_minutes" in _thr:
            COOLDOWN_MINUTES = _to_int(_thr["cooldown_minutes"], COOLDOWN_MINUTES)

        # Watchlist (top-level list)
        _wl = _cfg.get("watchlist", None)
        if isinstance(_wl, list) and _wl:
            WATCHLIST = [str(sym).strip().upper() for sym in _wl if str(sym).strip()]

        print(f"[config] Loaded conditions.json successfully.")

    except Exception as e:
        print(f"[config] WARNING: Failed to load conditions.json: {e}")

# ──────────────────────────────────────────────
# 3. Startup validation – warn if critical keys are empty
# ──────────────────────────────────────────────
if not UPSTOX_CLIENT_ID:
    print("[config] WARNING: UPSTOX_CLIENT_ID is empty! Login will fail.")
if not UPSTOX_CLIENT_SECRET:
    print("[config] WARNING: UPSTOX_CLIENT_SECRET is empty! Login will fail.")
if not TELEGRAM_BOT_TOKEN:
    print("[config] WARNING: TELEGRAM_BOT_TOKEN is empty! Alerts will not be sent.")
if not TELEGRAM_CHAT_ID:
    print("[config] WARNING: TELEGRAM_CHAT_ID is empty! Alerts will not be sent.")

print(f"[config] UPSTOX_CLIENT_ID = {UPSTOX_CLIENT_ID[:8]}..." if UPSTOX_CLIENT_ID else "[config] UPSTOX_CLIENT_ID = (empty)")
print(f"[config] TELEGRAM_BOT_TOKEN = {TELEGRAM_BOT_TOKEN[:10]}..." if TELEGRAM_BOT_TOKEN else "[config] TELEGRAM_BOT_TOKEN = (empty)")
print(f"[config] BASIS_THRESHOLD = {BASIS_THRESHOLD}, SPREAD_MIN = {SPREAD_MIN}, SPREAD_MAX = {SPREAD_MAX}")
print(f"[config] WATCHLIST = {WATCHLIST[:5]}{'...' if len(WATCHLIST) > 5 else ''}")
