from datetime import datetime
import pytz
from apscheduler.schedulers.blocking import BlockingScheduler

# Hardcoded NSE Holidays for 2026
NSE_HOLIDAYS_2026 = [
    "2026-01-26",  # Republic Day
    "2026-03-03",  # Holi
    "2026-03-26",  # Shri Ram Navami
    "2026-03-31",  # Shri Mahavir Jayanti
    "2026-04-03",  # Good Friday
    "2026-04-14",  # Dr. Baba Saheb Ambedkar Jayanti
    "2026-05-01",  # Maharashtra Day
    "2026-05-28",  # Bakri Id
    "2026-06-26",  # Muharram
    "2026-09-14",  # Ganesh Chaturthi
    "2026-10-02",  # Gandhi Jayanti
    "2026-10-20",  # Dussehra
    "2026-11-10",  # Diwali Balipratipada
    "2026-11-24",  # Guru Nanak Jayanti
    "2026-12-25"   # Christmas
]


def is_trading_day() -> bool:
    """
    Returns False for weekends and holidays
    """
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # Check if weekend (Saturday is 5, Sunday is 6)
    if now.weekday() >= 5:
        return False
        
    # Check if holiday
    date_str = now.strftime("%Y-%m-%d")
    if date_str in NSE_HOLIDAYS_2026:
        return False
        
    return True


def get_scheduler(market_open_fn, market_close_fn) -> BlockingScheduler:
    """
    Returns APScheduler BlockingScheduler with Asia/Kolkata timezone:
    - market_open_fn runs at 09:15 Mon-Fri
    - market_close_fn runs at 15:30 Mon-Fri
    """
    tz = pytz.timezone('Asia/Kolkata')
    scheduler = BlockingScheduler(timezone=tz)

    def open_job():
        if is_trading_day():
            market_open_fn()

    def close_job():
        if is_trading_day():
            market_close_fn()

    scheduler.add_job(
        open_job,
        'cron',
        day_of_week='mon-fri',
        hour=9,
        minute=15,
        id='market_open'
    )
    
    scheduler.add_job(
        close_job,
        'cron',
        day_of_week='mon-fri',
        hour=15,
        minute=30,
        id='market_close'
    )

    return scheduler
