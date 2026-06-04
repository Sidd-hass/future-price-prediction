# Futures Alert – NSE Futures & Options Scanner

## Overview
This repository continuously scans the National Stock Exchange (NSE) Futures‑and‑Options (F&O) segment, computes **basis** (difference between spot and near‑month futures) and **spread** (difference between consecutive futures contracts), and sends real-time Telegram alerts to all registered subscribers when target conditions are met:

- **Basis** > `BASIS_MIN` (default 2%)
- **Spread** ∈ [`SPREAD_MIN`, `SPREAD_MAX`] (default 0% – 0.7%)

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

### `auth_server.py`
- Acquires OAuth credentials from Upstox.
- Supports **silent (automatic) login** if Upstox credentials (`UPSTOX_USERNAME`, `UPSTOX_PASSWORD`, etc.) are configured in `.env`, using `upstox-totp` to write access tokens to `token.txt` instantly.
- Falls back to manual authorization with a local webserver callback on port 5000 if automatic login credentials are not set.
- **Run**: `python auth_server.py`

### `instruments.py`
- Downloads and parses the instruments file from Upstox (NSE segment).
- Caches results to avoid redownloading on every start and resolves active spot/futures contract keys.

### `config.py`
- Loads system environment settings and alerts configurations from `.env`.

---

## Quick Start Guide

1. **Install dependencies**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```
2. **Configure secrets** – Copy `.env.example` to `.env` and fill in your Upstox API credentials, Telegram Bot Token, and (optionally) your Upstox login credentials to enable silent token refreshes.
3. **Obtain an access token** (once per day)
   ```bash
   python auth_server.py
   ```
4. **Subscribe to alerts**
   - Open your Telegram bot link (e.g., `https://t.me/your_bot_name`).
   - Tap **Start** or send `/start` to subscribe.
5. **Run the scanner**
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

1. **Prepare configuration files**
   Ensure `.env`, `conditions.json`, and `token.txt` are created in the project root. Also, ensure the database file exists so Docker doesn't mistakenly create a directory:
   ```bash
   touch alerts.db
   ```
2. **Build and start the container**
   ```bash
   docker-compose up -d --build
   ```
   The container will automatically restart on failure and run in the background.

3. **Check the logs**
   ```bash
   docker-compose logs -f
   ```

4. **Updating settings**
   If you change `.env` or `conditions.json`, you should restart the container:
   ```bash
   docker-compose restart
   ```

---

## Technical Features
- **Dynamic Subscriber Management**: SQLite database persists registered user IDs. Adding new users doesn't require hardcoding.
- **WebSocket Feed Integration**: Real-time Protobuf-decoded price stream from Upstox.
- **Noise Filtering & Cooldown**: Filters out momentary price spikes (requires 5 consecutive ticks to trigger) and puts alerts on a 15-minute cooldown per stock.
