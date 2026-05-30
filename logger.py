import sqlite3
from datetime import datetime

def init_db(db_path: str = "alerts.db"):
    """
    Creates SQLite table alerts with columns:
    id, timestamp, symbol, spot, cur_fut, nxt_fut, 
    basis_pct, spread_pct, cur_expiry, nxt_expiry
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            spot REAL,
            cur_fut REAL,
            nxt_fut REAL,
            basis_pct REAL,
            spread_pct REAL,
            cur_expiry TEXT,
            nxt_expiry TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_alert(db_path: str, symbol: str, spot: float, cur_fut: float, nxt_fut: float, 
              basis: float, spread: float, cur_expiry: str, nxt_expiry: str):
    """
    Inserts one row into alerts table
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO alerts (
            timestamp, symbol, spot, cur_fut, nxt_fut, 
            basis_pct, spread_pct, cur_expiry, nxt_expiry
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, symbol, spot, cur_fut, nxt_fut, basis, spread, cur_expiry, nxt_expiry))
    conn.commit()
    conn.close()


def get_recent_alerts(db_path: str, limit: int = 20) -> list:
    """
    Returns last N alerts as list of dicts, ordered newest first
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, timestamp, symbol, spot, cur_fut, nxt_fut, 
               basis_pct, spread_pct, cur_expiry, nxt_expiry
        FROM alerts
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]
