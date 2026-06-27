# Futures Alert — System Documentation

## What You Built

**Futures Alert** is an automated stock market surveillance system that monitors NSE (National Stock Exchange of India) futures in real-time and sends instant Telegram notifications when it detects a specific pricing anomaly — **futures trading at a significant discount to the spot price while the calendar spread remains tight**.

---

## The Problem It Solves

### Background: How Futures Pricing Works

In a normal market, stock futures trade at a **slight premium** to the spot (cash) price. This premium exists because of the **cost of carry** — the interest cost of holding the position until expiry.

```
Normal:  Future Price  >  Spot Price   (premium — expected)
Anomaly: Future Price  <  Spot Price   (discount — unusual)
```

### When Futures Trade at a Discount

Sometimes, due to heavy selling pressure, panic, or institutional unwinding, the **futures price drops below the spot price**. This creates what's called a **basis discount**.

> [!IMPORTANT]
> A futures discount of **>2%** is unusual and can signal:
> - Heavy institutional selling / unwinding
> - A potential short-term buying opportunity (mean reversion)
> - Market stress or event-driven dislocation

### Why the Calendar Spread Matters

The app also checks that the **spread between current and next month futures is tight (0%–0.2%)**. A tight spread confirms:
- The discount is **structural**, not just an expiry-related distortion
- Both months are pricing similarly, meaning the market broadly expects this level
- It's not an artefact of low liquidity in one contract

### The Opportunity

By detecting these conditions **in real-time** (rather than manually checking charts), a trader can act quickly on potential mean-reversion trades before the market corrects.

---

## System Architecture

```mermaid
graph TB
    subgraph External Services
        UPSTOX_CSV["Upstox Instruments CSV<br/>(92,000+ instruments)"]
        UPSTOX_WS["Upstox WebSocket API<br/>(Real-time price feed)"]
        TG["Telegram Bot API"]
    end

    subgraph Futures Alert Application
        direction TB
        
        subgraph Startup Phase
            INST["instruments.py<br/>Download & Resolve Contracts"]
            CFG["config.py<br/>Load Environment Variables"]
        end

        subgraph Runtime Phase
            FEED["data_feed.py<br/>WebSocket Price Consumer"]
            CALC["calculator.py<br/>Basis & Spread Formulas"]
            ENGINE["alert_logic.py<br/>Conditions + Noise Filter + Cooldown"]
            BOT["telegram_bot.py<br/>Telegram Bot Listener"]
        end

        subgraph Output Phase
            NOTIFY["notifier.py<br/>Telegram Broadcaster"]
            LOG["logger.py<br/>SQLite Handler"]
        end

        SCHED["scheduler.py<br/>Market Hours Controller"]
        MAIN["main.py<br/>Orchestrator"]
    end

    subgraph Storage
        DB[("alerts.db<br/>SQLite<br/>(alerts, users, config)")]
        CACHE["instruments_cache.csv"]
    end

    CFG -->|"watchlist + thresholds + token"| MAIN
    UPSTOX_CSV -->|"gzip download"| INST
    INST -->|"cache"| CACHE
    INST -->|"instrument keys"| MAIN
    MAIN -->|"start/stop"| FEED
    MAIN -->|"spins up"| BOT
    SCHED -->|"09:15 open / 15:30 close"| MAIN
    UPSTOX_WS -->|"live LTP ticks"| FEED
    FEED -->|"spot, cur_fut, nxt_fut"| CALC
    CALC -->|"basis%, spread%"| ENGINE
    ENGINE -->|"alert signal"| NOTIFY
    ENGINE -->|"alert signal"| LOG
    NOTIFY -->|"broadcasts"| TG
    NOTIFY -->|"removes blocked users"| DB
    BOT <-->|"polls updates"| TG
    BOT -->|"registers subscribers"| DB
    LOG -->|"INSERT"| DB
```

---

## How Data Flows — Step by Step

```mermaid
sequenceDiagram
    participant User
    participant Main as main.py
    participant Inst as instruments.py
    participant Upstox as Upstox API
    participant Feed as data_feed.py
    participant Calc as calculator.py
    participant Engine as alert_logic.py
    participant Notifier as notifier.py
    participant Telegram as Telegram
    participant DB as SQLite

    User->>Main: python main.py
    Main->>Main: Load config & analytics token
    Main->>Inst: download_instruments()
    Inst->>Upstox: GET NSE.csv.gz (92K instruments)
    Upstox-->>Inst: CSV data
    Inst-->>Main: Instrument keys for watchlist stocks

    Note over Main: Wait for 09:15 IST or connect immediately

    Main->>Feed: connect()
    Feed->>Upstox: WebSocket subscribe (keys)
    
    loop Every price tick during market hours
        Upstox-->>Feed: LTP update (protobuf)
        Feed->>Feed: Parse LTP, update prices dict
        
        alt All 3 prices available for a stock
            Feed->>Calc: on_tick(symbol, spot, cur_fut, nxt_fut)
            Calc->>Calc: basis = ((spot-cur)/spot)×100
            Calc->>Calc: spread = ((nxt-cur)/cur)×100
            Calc->>Engine: should_alert(symbol, basis, spread)
            
            alt Conditions met (basis>2%, spread 0-0.2%)
                Engine->>Engine: Increment breach counter
                
                alt 5th consecutive breach
                    Engine-->>Notifier: FIRE ALERT
                    Notifier->>Telegram: POST /sendMessage
                    Telegram-->>User: 🚨 Alert notification
                    Engine->>DB: log_alert(...)
                    Engine->>Engine: Start 15-min cooldown
                end
            else Conditions NOT met
                Engine->>Engine: Reset breach counter to 0
            end
        end
    end

    Note over Main: 15:30 IST — Market closes
    Main->>Feed: disconnect()
```

---

## Alert Decision Logic

```mermaid
flowchart TD
    TICK["📊 New Price Tick Received"] --> PARSE["Parse LTP from WebSocket message"]
    PARSE --> CHECK_ALL{"All 3 prices<br/>available?<br/>(spot + cur_fut + nxt_fut)"}
    
    CHECK_ALL -->|No| WAIT["Wait for more ticks"]
    CHECK_ALL -->|Yes| CALC["Calculate:<br/>Basis = ((spot-cur)/spot)×100<br/>Spread = ((nxt-cur)/cur)×100"]
    
    CALC --> COND{"Basis > 2.0%<br/>AND<br/>0.0% ≤ Spread ≤ 0.2%?"}
    
    COND -->|No| RESET["Reset breach counter → 0"]
    RESET --> WAIT
    
    COND -->|Yes| INC["Increment breach counter"]
    INC --> NOISE{"Counter reached 5?<br/>(noise filter)"}
    
    NOISE -->|No| WAIT
    NOISE -->|Yes| COOL{"Cooldown active?<br/>(last alert < 15 min ago)"}
    
    COOL -->|Yes| WAIT
    COOL -->|No| ALERT["🚨 SEND ALERT"]
    
    ALERT --> TG["📱 Telegram notification"]
    ALERT --> DB["💾 Log to SQLite"]
    ALERT --> CD["⏱️ Start 15-min cooldown"]
    ALERT --> RST["Reset breach counter → 0"]
    
    TG --> WAIT
    
    style ALERT fill:#22c55e,color:#fff
    style COND fill:#f59e0b,color:#fff
    style NOISE fill:#f59e0b,color:#fff
    style COOL fill:#f59e0b,color:#fff
    style RESET fill:#ef4444,color:#fff
```

---

## Module Breakdown

| Module | Role | Key Functions |
|--------|------|---------------|
| [config.py](file:///c:/Users/jal/Downloads/futures-alert/futures-alert/config.py) | Loads all settings from `.env` or `conditions.json` | Environment variables/JSON → Python constants |
| [instruments.py](file:///c:/Users/jal/Downloads/futures-alert/futures-alert/instruments.py) | Downloads & parses 92K NSE instruments | `download_instruments()`, `get_active_contracts()` |
| [calculator.py](file:///c:/Users/jal/Downloads/futures-alert/futures-alert/calculator.py) | Pure math — two formulas | `compute_basis()`, `compute_spread()` |
| [alert_logic.py](file:///c:/Users/jal/Downloads/futures-alert/futures-alert/alert_logic.py) | Brain — conditions + noise + cooldown | `AlertEngine.should_alert()` |
| [data_feed.py](file:///c:/Users/jal/Downloads/futures-alert/futures-alert/data_feed.py) | WebSocket consumer for live prices | `PriceFeed.connect()`, `_on_message()` |
| [telegram_bot.py](file:///c:/Users/jal/Downloads/futures-alert/futures-alert/telegram_bot.py) | Background poller for sub requests | `poll_updates()`, `start_telegram_bot_thread()` |
| [notifier.py](file:///c:/Users/jal/Downloads/futures-alert/futures-alert/notifier.py) | Sends/broadcasts Telegram alerts | `send_telegram()`, `broadcast_telegram()` |
| [logger.py](file:///c:/Users/jal/Downloads/futures-alert/futures-alert/logger.py) | Persists alerts & subscriber DB tables | `init_db()`, `register_telegram_user()`, `get_registered_users()` |
| [scheduler.py](file:///c:/Users/jal/Downloads/futures-alert/futures-alert/scheduler.py) | Auto start/stop at market hours | `is_trading_day()`, `get_scheduler()` |
| [main.py](file:///c:/Users/jal/Downloads/futures-alert/futures-alert/main.py) | Ties everything together | Entry point |

---

## Technology Stack

```mermaid
graph LR
    subgraph Language
        PY["Python 3.12"]
    end
    
    subgraph Data
        PD["Pandas"]
        SQ["SQLite"]
    end
    
    subgraph Networking
        WS["WebSocket Client"]
        RQ["Requests"]
        PB["Protobuf"]
    end
    
    subgraph APIs
        UP["Upstox Python SDK"]
    end
    
    subgraph Scheduling
        AP["APScheduler"]
        TZ["pytz"]
    end
    
    subgraph Deployment
        DK["Docker"]
        DC["Docker Compose"]
    end
```

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | Python 3.12 | Core runtime |
| Data Processing | Pandas | Parse 92K instrument CSV |
| Database | SQLite | Store alert history locally |
| Real-time Feed | WebSocket + Protobuf | Receive live price ticks from Upstox |
| HTTP | Requests | Download instruments CSV, send Telegram messages |
| Scheduling | APScheduler + pytz | Cron jobs in Asia/Kolkata timezone |
| Config | python-dotenv | Load `.env` file variables |
| Deployment | Docker + Docker Compose | Container-based deployment |

---

## Deployment Architecture

```mermaid
graph TB
    subgraph Docker Container
        APP["futures-alert<br/>(Python 3.12-slim)"]
    end

    subgraph Mounted Volumes
        V2["alerts.db<br/>(Alert history)"]
        V3["instruments_cache.csv<br/>(Cached instruments)"]
        V4["conditions.json<br/>(Runtime overrides)"]
    end

    subgraph External
        UP["Upstox WebSocket"]
        TG["Telegram API"]
    end

    V2 --> APP
    V3 --> APP
    V4 --> APP
    APP <-->|"wss://"| UP
    APP -->|"HTTPS POST"| TG
```

The app runs as a single long-lived Docker container that:
- Starts automatically on boot (`restart: always`)
- Reads credentials from `.env` or `conditions.json`
- Persists alert history via the mounted `alerts.db` volume
- Caches the instruments CSV to avoid re-downloading on restart

---

## Summary

| Aspect | Detail |
|--------|--------|
| **What** | Real-time NSE futures discount detector with Telegram alerts |
| **Problem** | Manually monitoring futures-vs-spot pricing across stocks is impractical |
| **Solution** | Automated WebSocket-based surveillance with configurable thresholds |
| **Signal** | Futures discount > 2% AND calendar spread between 0–0.2% |
| **Noise Reduction** | 5 consecutive tick confirmation + 15-min cooldown per stock |
| **Output** | Instant Telegram notification + SQLite audit trail |
| **Schedule** | Auto-runs during NSE market hours (09:15–15:30 IST, Mon–Fri, skipping holidays) |
