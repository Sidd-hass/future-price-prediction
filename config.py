import json
from pathlib import Path

# Path to the optional conditions JSON file
_conditions_path = Path(__file__).parent / "conditions.json"

# Default configuration values (same as original defaults)
_DEFAULTS = {
    "UPSTOX_ACCESS_TOKEN": "",
    "UPSTOX_CLIENT_ID": "",
    "UPSTOX_CLIENT_SECRET": "",
    "TELEGRAM_BOT_TOKEN": "",
    "TELEGRAM_CHAT_ID": "",
    "BASIS_THRESHOLD": 2.0,
    "SPREAD_MIN": 0.0,
    "SPREAD_MAX": 0.2,
    "BREACH_COUNT_THRESHOLD": 5,
    "COOLDOWN_MINUTES": 15,
    "WATCHLIST": ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
}

# Load configuration from conditions.json if it exists; otherwise fall back to defaults
if _conditions_path.is_file():
    try:
        with open(_conditions_path, "r", encoding="utf-8") as f:
            _config = json.load(f)
    except Exception:
        _config = {}
else:
    _config = {}

# Helper to fetch a value with fallback to defaults
def _get(key, default=None):
    return _config.get(key, _DEFAULTS.get(key, default))

# Assign configuration variables
UPSTOX_ACCESS_TOKEN = _get("UPSTOX_ACCESS_TOKEN", "")
UPSTOX_CLIENT_ID = _get("UPSTOX_CLIENT_ID", "")
UPSTOX_CLIENT_SECRET = _get("UPSTOX_CLIENT_SECRET", "")

TELEGRAM_BOT_TOKEN = _get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = _get("TELEGRAM_CHAT_ID", "")

BASIS_THRESHOLD = float(_get("BASIS_MIN", 2.0))
SPREAD_MIN = float(_get("SPREAD_MIN", 0.0))
SPREAD_MAX = float(_get("SPREAD_MAX", 0.2))
BREACH_COUNT_THRESHOLD = int(_get("BREACH_COUNT_THRESHOLD", 5))

COOLDOWN_MINUTES = int(_get("COOLDOWN_MINUTES", 15))

# WATCHLIST may be provided as a list or a comma‑separated string
_watchlist = _get("WATCHLIST", None)
if isinstance(_watchlist, str):
    WATCHLIST = [sym.strip().upper() for sym in _watchlist.split(",") if sym.strip()]
elif isinstance(_watchlist, list):
    WATCHLIST = [_sym.upper() for _sym in _watchlist]
else:
    WATCHLIST = _DEFAULTS["WATCHLIST"]

# Nested sections handling
telegram_cfg = _config.get("TELEGRAM", {})
if isinstance(telegram_cfg, dict):
    TELEGRAM_BOT_TOKEN = telegram_cfg.get("BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = telegram_cfg.get("CHAT_ID", "")
else:
    TELEGRAM_BOT_TOKEN = ""
    TELEGRAM_CHAT_ID = ""

upstox_cfg = _config.get("UPSTOX", {})
if isinstance(upstox_cfg, dict):
    UPSTOX_CLIENT_ID = upstox_cfg.get("API_KEY", "")
    UPSTOX_CLIENT_SECRET = upstox_cfg.get("API_SECRET", "")
else:
    UPSTOX_CLIENT_ID = ""
    UPSTOX_CLIENT_SECRET = ""


