"""
Integration test for the entire futures-alert codebase.
Tests each module with real/simulated data and sends a live Telegram message.
Run: PYTHONPATH=. venv/Scripts/python tests/test_integration.py
"""
import os
import sys
import tempfile

# ── Ensure we are in project root ────────────────────────────────────────────
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

passed = 0
failed = 0
total = 0

def report(name, ok, detail=""):
    global passed, failed, total
    total += 1
    if ok:
        passed += 1
        print(f"  [OK]  {name}")
    else:
        failed += 1
        print(f"  [FAIL]  {name}  -  {detail}")


def main():
    print("\n" + "=" * 60)
    print("  FUTURES-ALERT  -  INTEGRATION TEST")
    print("=" * 60)

    # ==============================================================================
    # 1. CONFIG
    # ==============================================================================
    print("\n--- 1. config.py ---")
    try:
        import config
        report("ANALYTICS_TOKEN loaded",        bool(config.ANALYTICS_TOKEN))
        report("TELEGRAM_BOT_TOKEN loaded",    bool(config.TELEGRAM_BOT_TOKEN))
        report("TELEGRAM_CHAT_ID loaded",      bool(config.TELEGRAM_CHAT_ID))
        report("WATCHLIST is a list",          isinstance(config.WATCHLIST, list) and len(config.WATCHLIST) > 0)
        report("BASIS_THRESHOLD is float",     isinstance(config.BASIS_THRESHOLD, float))
        report("BREACH_COUNT_THRESHOLD is int", isinstance(config.BREACH_COUNT_THRESHOLD, int))
    except Exception as e:
        report("config import", False, str(e))

    # ==============================================================================
    # 2. CALCULATOR
    # ==============================================================================
    print("\n--- 2. calculator.py ---")
    try:
        from calculator import compute_basis, compute_spread

        b = compute_basis(1000.0, 975.0)
        report(f"compute_basis(1000, 975) = {b:.2f}%", abs(b - 2.5) < 0.01)

        s = compute_spread(975.0, 976.0)
        report(f"compute_spread(975, 976) = {s:.4f}%", abs(s - 0.1026) < 0.01)

        report("compute_basis(0, 100) handles zero", compute_basis(0, 100) == 0.0)
        report("compute_spread(0, 100) handles zero", compute_spread(0, 100) == 0.0)
    except Exception as e:
        report("calculator import", False, str(e))

    # ==============================================================================
    # 3. ALERT ENGINE
    # ==============================================================================
    print("\n--- 3. alert_logic.py ---")
    try:
        from alert_logic import AlertEngine

        engine = AlertEngine(config)

        # Conditions check
        report("check_conditions(2.5, 0.1) = True",  engine.check_conditions(2.5, 0.1))
        report("check_conditions(1.0, 0.1) = False",  not engine.check_conditions(1.0, 0.1))
        report("check_conditions(2.5, 0.6) = False",  not engine.check_conditions(2.5, config.SPREAD_MAX + 0.1))

        # Noise filter: send 5 consecutive breach ticks
        sym = config.WATCHLIST[0]
        for i in range(config.BREACH_COUNT_THRESHOLD - 1):
            engine.noise_filter(sym, 3.0, 0.1)
        fires = engine.noise_filter(sym, 3.0, 0.1)
        report(f"noise_filter fires on tick #{config.BREACH_COUNT_THRESHOLD}", fires)

        # Cooldown
        engine.record_alert(sym)
        report("cooldown active after record_alert", engine.is_cooldown_active(sym))

        # Reset
        engine.reset_breach(sym)
        report("breach counter resets to 0", engine.breach_counter[sym] == 0)
    except Exception as e:
        report("alert_logic import", False, str(e))

    # ==============================================================================
    # 4. LOGGER (SQLite)
    # ==============================================================================
    print("\n--- 4. logger.py ---")
    try:
        from logger import init_db, log_alert, get_recent_alerts

        with tempfile.NamedTemporaryFile(suffix=".db", dir=".", delete=False) as tmp:
            test_db = tmp.name

        init_db(test_db)
        report("init_db creates database file", os.path.exists(test_db))

        log_alert(test_db, "RELIANCE", 1000, 975, 976, 2.5, 0.1, "2026-06-30", "2026-07-28")
        log_alert(test_db, "TCS",      3500, 3430, 3433, 2.0, 0.08, "2026-06-30", "2026-07-28")
        alerts = get_recent_alerts(test_db, limit=10)
        report(f"logged 2 alerts, retrieved {len(alerts)}", len(alerts) == 2)
        report("newest alert is TCS", alerts[0]["symbol"] == "TCS")
        report("alert has all fields", all(k in alerts[0] for k in ["timestamp", "spot", "basis_pct", "spread_pct"]))

        os.unlink(test_db)
    except Exception as e:
        report("logger import", False, str(e))

    # ==============================================================================
    # 5. INSTRUMENTS (mock DataFrame)
    # ==============================================================================
    print("\n--- 5. instruments.py ---")
    try:
        import pandas as pd
        from instruments import get_active_contracts

        mock_data = pd.DataFrame([
            {"instrument_key": "NSE_EQ|INE002A01018", "tradingsymbol": "RELIANCE",
             "name": "RELIANCE INDUSTRIES LTD", "expiry": "", "instrument_type": "EQUITY",
             "exchange": "NSE_EQ"},
            {"instrument_key": "NSE_FO|62802", "tradingsymbol": "RELIANCE26JUNFUT",
             "name": "RELIANCE INDUSTRIES LTD", "expiry": "2026-06-30",
             "instrument_type": "FUTSTK", "exchange": "NSE_FO"},
            {"instrument_key": "NSE_FO|61284", "tradingsymbol": "RELIANCE26JULFUT",
             "name": "RELIANCE INDUSTRIES LTD", "expiry": "2026-07-28",
             "instrument_type": "FUTSTK", "exchange": "NSE_FO"},
        ])

        contracts = get_active_contracts("RELIANCE", mock_data)
        report("spot_key resolved",    contracts["spot_key"] == "NSE_EQ|INE002A01018")
        report("cur_fut sorted first", contracts["cur_expiry"] == "2026-06-30")
        report("nxt_fut sorted second", contracts["nxt_expiry"] == "2026-07-28")

        # Test error on insufficient futures
        try:
            get_active_contracts("RELIANCE", mock_data.iloc[:2])
            report("ValueError on <2 futures", False, "no exception raised")
        except ValueError:
            report("ValueError on <2 futures", True)
    except Exception as e:
        report("instruments import", False, str(e))

    # ==============================================================================
    # 6. DATA FEED (message parsing)
    # ==============================================================================
    print("\n--- 6. data_feed.py (message parsing) ---")
    try:
        from data_feed import PriceFeed

        ticks_received = []

        def mock_callback(symbol, spot, cur_fut, nxt_fut):
            ticks_received.append((symbol, spot, cur_fut, nxt_fut))

        instrument_map = {
            "RELIANCE": {
                "spot_key": "NSE_EQ|INE002A01018",
                "cur_fut_key": "NSE_FO|62802",
                "nxt_fut_key": "NSE_FO|61284",
            }
        }

        # Create PriceFeed without connecting (no access token needed for parse test)
        feed = PriceFeed.__new__(PriceFeed)
        feed.instrument_map = instrument_map
        feed.on_tick_callback = mock_callback
        feed.prices = {}
        feed.key_to_symbol = {}
        feed.keys = []
        for sym, info in instrument_map.items():
            for k in [info["spot_key"], info["cur_fut_key"], info["nxt_fut_key"]]:
                feed.key_to_symbol[k] = sym

        # Simulate a websocket message with all 3 prices
        fake_message = {
            "feeds": {
                "NSE_EQ|INE002A01018": {"ltpc": {"ltp": 1000.0}},
                "NSE_FO|62802":       {"ltpc": {"ltp": 975.0}},
                "NSE_FO|61284":       {"ltpc": {"ltp": 976.0}},
            }
        }
        feed._on_message(fake_message)

        report("callback fired on complete tick", len(ticks_received) > 0)
        if ticks_received:
            sym, sp, cf, nf = ticks_received[-1]
            report(f"tick values: spot={sp}, cur={cf}, nxt={nf}",
                   sym == "RELIANCE" and sp == 1000.0 and cf == 975.0 and nf == 976.0)

        # Test nested fullFeed format
        feed.prices = {}
        ticks_received.clear()
        nested_message = {
            "feeds": {
                "NSE_EQ|INE002A01018": {"fullFeed": {"marketFF": {"ltpc": {"ltp": 1001.0}}}},
                "NSE_FO|62802":       {"fullFeed": {"marketFF": {"ltpc": {"ltp": 976.0}}}},
                "NSE_FO|61284":       {"fullFeed": {"marketFF": {"ltpc": {"ltp": 977.0}}}},
            }
        }
        feed._on_message(nested_message)
        report("nested fullFeed format parsed", len(ticks_received) > 0)
    except Exception as e:
        report("data_feed parsing", False, str(e))

    # ==============================================================================
    # 7. SCHEDULER
    # ==============================================================================
    print("\n--- 7. scheduler.py ---")
    try:
        from scheduler import is_trading_day, NSE_HOLIDAYS_2026

        report(f"NSE holidays list has {len(NSE_HOLIDAYS_2026)} entries", len(NSE_HOLIDAYS_2026) >= 10)
        report("is_trading_day() returns bool", isinstance(is_trading_day(), bool))
    except Exception as e:
        report("scheduler import", False, str(e))

    # ==============================================================================
    # 8. NOTIFIER (live Telegram)
    # ==============================================================================
    print("\n--- 8. notifier.py (LIVE Telegram send) ---")
    try:
        from notifier import send_telegram

        resp = send_telegram(
            bot_token=config.TELEGRAM_BOT_TOKEN,
            chat_id=config.TELEGRAM_CHAT_ID,
            symbol="RELIANCE",
            spot=1000.0,
            cur_fut=975.0,
            nxt_fut=976.0,
            basis=2.50,
            spread=0.10,
            cur_expiry="2026-06-30",
            nxt_expiry="2026-07-28"
        )
        report(f"Telegram send status={resp.status_code}", resp.status_code == 200)
    except Exception as e:
        report("notifier send", False, str(e))

    # ==============================================================================
    # SUMMARY
    # ==============================================================================
    print("\n" + "=" * 60)
    if failed == 0:
        print(f"  [SUCCESS]  ALL {total} CHECKS PASSED")
    else:
        print(f"  [WARNING]  {passed}/{total} passed, {failed} FAILED")
    print("=" * 60 + "\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
