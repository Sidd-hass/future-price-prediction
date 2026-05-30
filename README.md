# Futures Alert – NSE Futures & Options Scanner

## Overview
This repository continuously scans the National Stock Exchange (NSE) Futures‑and‑Options (F&O) segment, computes **basis** (difference between spot and near‑month futures) and **spread** (difference between consecutive futures contracts), and sends a Telegram alert when the following conditions are met:

- **Basis** > `BASIS_MIN` (default 2 %)
- **Spread** ∈ [`SPREAD_MIN`, `SPREAD_MAX`] (default 0 % – 0.7 %)

The system can operate in two modes:
1. **Test mode** – works on the last‑closed market data.
2. **Live (real‑world) mode** – fetches current LTP from Upstox and sends real alerts.

Below is a concise explanation of each file in the project.

---

### `auth_server.py`
- Implements a tiny Flask server that performs the OAuth 2.0 authorization code flow for Upstox.
- Handles the callback, exchanges the code for an access token, and writes the token to `token.txt`.
- Includes a fix that URL‑encodes the `redirect_uri` parameter to avoid *redirect_uri_mismatch* errors.
- **Run**: `python auth_server.py` – opens a browser for the user to log in and authorise.

---

### `main.py`
- Entry‑point for the continuous scanner.
- Parses command‑line flags (`--force` to run outside market hours, `--watchlist` to limit symbols).
- Loads configuration from `conditions.json` (including `WATCHLIST`, `BASIS_MIN`, `SPREAD_MAX`, etc.).
- Calls the pipeline defined in `alert_logic.py` and loops with a configurable `SCAN_INTERVAL_SECONDS`.
- Sends alerts via `telegram_bot.py` (embedded in `alert_logic`).
- **Run**: `python main.py [--force]`

---

### `test_all_nse.py`
- One‑off script used for the **real‑world verification** you requested.
- Resolves **all** NSE F&O symbols (`WATCHLIST=ALL`), fetches spot & futures contracts, pulls LTPs from Upstox, computes basis/spread, prints a top‑15 table and sends real Telegram alerts for any stock meeting the thresholds.
- Useful for a quick sanity‑check without starting the long‑running daemon.
- **Run**: `python test_all_nse.py`

---

### `instruments.py`
- Contains helper functions to parse the `instruments.csv` file supplied by Upstox.
- Provides `load_instruments()`, `resolve_spot_and_futures(symbols)` and utilities to map NSE symbols to the required Upstox instrument keys.
- Used by both `main.py` and `test_all_nse.py`.

---

### `alert_logic.py`
- Core business logic:
  - `compute_basis(spot_price, fut_price)`
  - `compute_spread(cur_fut_price, nxt_fut_price)`
  - `check_alert_conditions(basis, spread, env)` – returns a boolean.
  - `send_telegram_alert(symbol, basis, spread)` – posts a formatted message via the bot token defined in `.env`.
- Centralises all thresholds and formatting, making it easy to tweak alert criteria.

---

### `requirements.txt`
- Lists the Python dependencies required to run the project, e.g.:
  ```
  flask
  upstox-api
  python-telegram-bot
  python-dotenv
  pandas
  ```
- Install with `pip install -r requirements.txt`.

---

73: ### `conditions.json`
74: - Central configuration file that the application now loads exclusively.
75: - **Key entries** (same as before):
76:   - `UPSTOX_API_KEY`, `UPSTOX_API_SECRET`
77:   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
78:   - `WATCHLIST` – either a list or "ALL" to scan the entire NSE F&O universe.
79:   - `BASIS_MIN`, `SPREAD_MIN`, `SPREAD_MAX`
80:   - `SCAN_INTERVAL_SECONDS` – seconds between scans.
81:   - `FORCE` – boolean to force run outside market hours.
82: - No `.env` file is required; keep credentials only in this JSON (do not commit to public repo).
- Environment configuration (loaded with `python-dotenv`).
- **Key entries**:
  - `UPSTOX_API_KEY`, `UPSTOX_API_SECRET`
  - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
  - `WATCHLIST` – either a comma‑separated list of symbols or `ALL`.
  - `BASIS_MIN`, `SPREAD_MIN`, `SPREAD_MAX`
  - `SCAN_INTERVAL` – seconds between scans.
  - `FORCE` – set to `1` to run regardless of market hours.
- **Do not** commit this file to a public repo – it contains secrets.

---

### `features.md`
- A living design document that outlines planned enhancements (e.g., automated TOTP‑based token refresh, Dockerisation, CI pipelines).
- Helpful for future contributors to see the roadmap.

---

### `docs/`
- Contains additional markdown documentation, such as deployment instructions, architecture diagrams, and troubleshooting tips.
- Not required for core execution but provides a richer context for developers.

---

## Quick Start Guide
1. **Install dependencies**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```
2. **Configure secrets** – copy `.env.example` to `.env` and fill in your Upstox API key/secret and Telegram bot credentials.
3. **Obtain an access token** (once per day)
   ```bash
   python auth_server.py
   ```
   Follow the browser prompt; the token will be saved to `token.txt`.
4. **Run a live scan** (continuous mode)
   ```bash
   python main.py --force   # --force optional, forces run outside market hours
   ```
5. **Run a one‑off verification** (real‑world alert)
   ```bash
   python test_all_nse.py
   ```
   The script prints a table and sends Telegram alerts for any qualifying stocks.

---

## Extending the Project
- To add **new alert criteria**, edit `alert_logic.check_alert_conditions`.
- To support **different exchanges**, extend `instruments.py` to parse the relevant CSV and map symbols.
- For **automated token refresh**, implement a scheduled TOTP generator (see the `features.md` roadmap).

---

*Happy hunting! 🎯*
