import os
import sqlite3
import pytest
from logger import init_db, log_alert, get_recent_alerts

def test_init_creates_table(tmp_path):
    db_file = tmp_path / "test_alerts.db"
    db_path = str(db_file)
    
    init_db(db_path)
    
    # Verify table exists and has correct columns
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(alerts)")
    columns = [row[1] for row in cursor.fetchall()]
    conn.close()
    
    expected_cols = [
        "id", "timestamp", "symbol", "spot", "cur_fut", 
        "nxt_fut", "basis_pct", "spread_pct", "cur_expiry", "nxt_expiry"
    ]
    for col in expected_cols:
        assert col in columns


def test_log_and_retrieve(tmp_path):
    db_file = tmp_path / "test_alerts.db"
    db_path = str(db_file)
    init_db(db_path)
    
    log_alert(
        db_path=db_path,
        symbol="RELIANCE",
        spot=1000.0,
        cur_fut=980.0,
        nxt_fut=981.0,
        basis=2.0,
        spread=0.1,
        cur_expiry="2026-06-30",
        nxt_expiry="2026-07-28"
    )
    
    alerts = get_recent_alerts(db_path, limit=20)
    assert len(alerts) == 1
    
    alert = alerts[0]
    assert alert["symbol"] == "RELIANCE"
    assert alert["spot"] == 1000.0
    assert alert["cur_fut"] == 980.0
    assert alert["nxt_fut"] == 981.0
    assert alert["basis_pct"] == 2.0
    assert alert["spread_pct"] == 0.1
    assert alert["cur_expiry"] == "2026-06-30"
    assert alert["nxt_expiry"] == "2026-07-28"
    assert "timestamp" in alert


def test_multiple_alerts_ordered(tmp_path):
    db_file = tmp_path / "test_alerts.db"
    db_path = str(db_file)
    init_db(db_path)
    
    # Log 3 alerts
    log_alert(db_path, "RELIANCE", 1000, 980, 981, 2.0, 0.1, "EXP1", "EXP2")
    log_alert(db_path, "TCS", 2000, 1960, 1962, 2.0, 0.1, "EXP1", "EXP2")
    log_alert(db_path, "INFY", 3000, 2940, 2943, 2.0, 0.1, "EXP1", "EXP2")
    
    alerts = get_recent_alerts(db_path, limit=20)
    assert len(alerts) == 3
    
    # Newest first: INFY, then TCS, then RELIANCE
    assert alerts[0]["symbol"] == "INFY"
    assert alerts[1]["symbol"] == "TCS"
    assert alerts[2]["symbol"] == "RELIANCE"


def test_telegram_user_registration(tmp_path):
    db_file = tmp_path / "test_alerts.db"
    db_path = str(db_file)
    init_db(db_path)
    
    from logger import register_telegram_user, unregister_telegram_user, get_registered_users
    
    # Verify initially empty
    assert get_registered_users(db_path) == []
    
    # Register a user
    register_telegram_user(db_path, "12345", "testuser", "Test", "User")
    assert get_registered_users(db_path) == ["12345"]
    
    # Register another user
    register_telegram_user(db_path, "67890", "anotheruser")
    assert sorted(get_registered_users(db_path)) == ["12345", "67890"]
    
    # Unregister a user
    unregister_telegram_user(db_path, "12345")
    assert get_registered_users(db_path) == ["67890"]


def test_bot_offset_management(tmp_path):
    db_file = tmp_path / "test_alerts.db"
    db_path = str(db_file)
    init_db(db_path)
    
    from logger import get_bot_offset, set_bot_offset
    
    # Verify initially None
    assert get_bot_offset(db_path) is None
    
    # Set offset
    set_bot_offset(db_path, 100)
    assert get_bot_offset(db_path) == 100
    
    # Update offset
    set_bot_offset(db_path, 101)
    assert get_bot_offset(db_path) == 101

