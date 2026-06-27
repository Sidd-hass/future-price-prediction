# Futures Alert – NSE Futures & Options Scanner

## Overview
This repository continuously scans the National Stock Exchange (NSE) Futures‑and‑Options (F&O) segment, computes **basis** (difference between spot and near‑month futures) and **spread** (difference between consecutive futures contracts), and sends real-time Telegram alerts to all registered subscribers when target conditions are met:

- **Basis** > `BASIS_MIN` (default 2%)
- **Spread** &isin; [`SPREAD_MIN`, `SPREAD_MAX`] (default 0% – 0.5%)

The system supports two modes of execution:
1. **Test/Simulated mode** (`test_all_nse.py`) – performs a one-off scan of the entire NSE F&O universe using current market prices and sends simulated/real alerts.
2. **Live mode** (`main.py`) – runs a continuous WebSocket stream from Upstox, processes live price ticks, and broadcasts signals to subscribers.

---

## File Structure & Module Breakdown

### `main.py`
- Entry-point for the continuous scanner daemon.
- Connects to the Upstox live price WebSocket feed and processes ticks during NSE trading hours (using `scheduler.py`).
- Spins up a background Telegram bot poller thread to dynamically handle subscription commands.
- Broadcasts detected arbitrage opportunities to all registered subscribers.
- **Run**: `python main.py [--force]` (use `--force` to connect immediately outside market hours)

### `telegram_bot.py`
- Implements a background updates poller using standard HTTP long-polling to Telegram's `getUpdates` API.
- Handles user subscription command flows:
  - `/start` – Registers the user's `chat_id` in the SQLite database and sends a confirmation greeting.
  - `/stop` – Unsubscribes the user by removing their record from the database.
  - `/status` – Checks and reports subscription status.
  - `/help` – Displays a helper menu of bot commands.

### `notifier.py`
- Formats and dispatches alerts via the Telegram Bot API.
- Includes `broadcast_telegram()` which iterates over all registered subscribers.
- **Automatic Cleanup**: Captures `403 Forbidden` (user blocked the bot) and `400` (chat not found) API errors to automatically unregister inactive or invalid chat IDs from the database, keeping the list clean.

### `logger.py`
- Manages local SQLite storage in `alerts.db`.
- Creates and maintains the tables:
  - `alerts` – Chronological audit trail of all generated signals and price levels.
  - `telegram_users` – Active subscriber chat IDs, usernames, and registration timestamps.
  - `bot_config` – State config values (e.g., last processed Telegram `update_id` offset to guarantee single-delivery of messages across restarts).
- Provides database helper operations for main logic and the bot thread.

### `test_all_nse.py`
- A runnable verification script that fetches live prices from Upstox REST API for all NSE F&O stocks.
- Computes basis/spread and displays a top-15 discount table in the console.
- Resolves subscribers from `alerts.db` and dispatches test alerts.
- **Run**: `python test_all_nse.py`

### `instruments.py`
- Downloads and parses the instruments file from Upstox (NSE segment).
- Caches results to avoid redownloading on every start and resolves active spot/futures contract keys.

### `config.py`
- Loads system environment settings and alerts configurations from `.env` or `conditions.json`.

---

## Quick Start Guide

### 1. Clone the repository and checkout the correct branch
```bash
git clone -b feat/analytics-token-docker https://github.com/Sidd-hass/future-price-prediction.git
cd future-price-prediction
```

### 2. Install dependencies
```bash
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate # macOS/Linux
pip install -r requirements.txt
```

### 3. Configure secrets
Copy `.env.example` to `.env` and fill in your Upstox `ANALYTICS_TOKEN` and Telegram Bot details:
```env
ANALYTICS_TOKEN=your_upstox_analytics_token_here
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```
Alternatively, configure them in `conditions.json` (values inside `conditions.json` will override `.env`).

### 4. Subscribe to alerts
- Open your Telegram bot link (e.g., `https://t.me/your_bot_name`).
- Tap **Start** or send `/start` to subscribe.

### 5. Run the scanner
- Run a one-off F&O scan with test alerts:
  ```bash
  python test_all_nse.py
  ```
- Start the continuous live price monitoring system:
  ```bash
  python main.py --force
  ```

---

## Running with Docker (Recommended for 24/7 Cloud)

If you are deploying this application on a cloud server for continuous monitoring, it is highly recommended to run it inside Docker.

### 1. Build and start the container
```bash
docker-compose up -d --build
```
The container will automatically restart on failure and run in the background.

### 2. Check the logs
```bash
docker-compose logs -f
```

### 3. Updating settings
If you change `.env` or `conditions.json`, you should restart the container:
```bash
docker-compose restart
```

---

## Technical Features
- **Dynamic Subscriber Management**: SQLite database persists registered user IDs. Adding new users doesn't require hardcoding.
- **WebSocket Feed Integration**: Real-time Protobuf-decoded price stream from Upstox.
- **Noise Filtering & Cooldown**: Filters out momentary price spikes (requires 5 consecutive ticks to trigger) and puts alerts on a 15-minute cooldown per stock.
