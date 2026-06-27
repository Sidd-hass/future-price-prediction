# Manual Run Guide for Futures‑Alert (Docker)

This document explains how to configure, build, and run the containerized application on a machine.

---

## 1. Prerequisites
- **Docker Desktop** installed and running.
- **PowerShell** (or Command Prompt) with access to the project folder.

---

## 2. Configuration Options

You can configure the application using either **`.env`** or **`conditions.json`**.

### Option A: Using `.env` (Recommended for Local Dev)
Ensure your `.env` contains the `ANALYTICS_TOKEN` and your Telegram details:
```env
ANALYTICS_TOKEN=your_upstox_analytics_token_here
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### Option B: Using `conditions.json` (Recommended for Production Config)
Your `conditions.json` file should contain the configurations:
```json
{
  "upstox": {
    "ANALYTICS_TOKEN": "your_upstox_analytics_token_here"
  },
  "telegram": {
    "TELEGRAM_BOT_TOKEN": "your_bot_token_here",
    "TELEGRAM_CHAT_ID": "your_chat_id_here"
  },
  "thresholds": {
    "basis_threshold": 2.0,
    "spread_min": 0.0,
    "spread_max": 0.5,
    "breach_count_threshold": 5,
    "cooldown_minutes": 15
  },
  "watchlist": [
    "ALL"
  ]
}
```

---

## 3. Build the Docker Image
Build the Docker image:
```powershell
docker build -t futures-alert:latest .
```
- `-t futures-alert:latest` tags the image.
- A `.dockerignore` file exists to ensure local temporary files like virtual environments (`venv`) and cached databases (`alerts.db`, `instruments_cache.csv`) are ignored during context build.

---

## 4. Run the Container

### Using Docker Compose (Recommended)
Run using Docker Compose:
```powershell
docker-compose up -d --build
```

### Using Raw Docker Run
If running directly with `docker run`:
```powershell
docker run -d --name futures-alert \
  -v "${PWD}/conditions.json:/app/conditions.json:ro" \
  -v "${PWD}/alerts.db:/app/alerts.db" \
  --env-file .env \
  futures-alert:latest
```
- Mounts `conditions.json` as read-only.
- Mounts `alerts.db` to persist user subscriptions and alert logs on the host.
