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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telegram_users (
            chat_id TEXT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            registered_at TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_config (
            key TEXT PRIMARY KEY,
            value TEXT
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


def register_telegram_user(db_path: str, chat_id: str, username: str = None, 
                           first_name: str = None, last_name: str = None):
    """
    Registers a telegram user by inserting or replacing their chat_id and details.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT OR REPLACE INTO telegram_users (chat_id, username, first_name, last_name, registered_at)
        VALUES (?, ?, ?, ?, ?)
    """, (str(chat_id), username, first_name, last_name, timestamp))
    conn.commit()
    conn.close()


def unregister_telegram_user(db_path: str, chat_id: str):
    """
    Unregisters a telegram user by deleting their chat_id.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM telegram_users WHERE chat_id = ?", (str(chat_id),))
    conn.commit()
    conn.close()


def get_registered_users(db_path: str) -> list:
    """
    Returns a list of all registered telegram user chat_ids.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM telegram_users")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


def get_bot_offset(db_path: str) -> int | None:
    """
    Gets the last processed update_id offset.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM bot_config WHERE key = 'last_update_id'")
    row = cursor.fetchone()
    conn.close()
    if row:
        try:
            return int(row[0])
        except ValueError:
            return None
    return None


def set_bot_offset(db_path: str, offset: int):
    """
    Sets the last processed update_id offset.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO bot_config (key, value)
        VALUES ('last_update_id', ?)
    """, (str(offset),))
    conn.commit()
    conn.close()

