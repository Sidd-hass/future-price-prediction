import logging
import sys
from datetime import datetime, time
import pytz
import config
from instruments import download_instruments, get_active_contracts
from calculator import compute_basis, compute_spread
from alert_logic import AlertEngine
from data_feed import PriceFeed
from notifier import send_telegram, broadcast_telegram
from logger import init_db, log_alert, get_registered_users
from scheduler import is_trading_day, get_scheduler
from telegram_bot import start_telegram_bot_thread


# Configure standard logging output to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("main")


def main():
    # 1. Initialize SQLite Database
    logger.info("Initializing SQLite database...")
    init_db("alerts.db")

    # 2. Load access token
    token = config.ANALYTICS_TOKEN
    if not token:
        logger.error("UPSTOX ANALYTICS_TOKEN is empty! Please set the ANALYTICS_TOKEN environment variable in your .env file.")
        sys.exit(1)

    # 3. Resolve active contracts
    logger.info("Fetching instruments list...")
    df = download_instruments()
    
    watchlist = config.WATCHLIST
    if len(watchlist) == 1 and watchlist[0] == "ALL":
        logger.info("Watchlist is set to 'ALL'. Dynamically resolving all F&O stocks from instruments list...")
        nse_fo_fut = df[(df['exchange'] == 'NSE_FO') & (df['instrument_type'] == 'FUTSTK')]
        nse_eq_symbols = set(df[df['exchange'] == 'NSE_EQ']['tradingsymbol'].unique())
        resolved_symbols = set()
        for t_symbol in nse_fo_fut['tradingsymbol'].unique():
            if t_symbol.endswith('FUT'):
                base = t_symbol[:-3]
                symbol = base[:-5]
                if symbol in nse_eq_symbols:
                    resolved_symbols.add(symbol)
        watchlist = sorted(list(resolved_symbols))
        logger.info(f"Dynamically resolved {len(watchlist)} F&O stocks to monitor.")

    logger.info("Building instrument map for the watchlist...")
    instrument_map = {}
    for symbol in watchlist:
        try:
            contracts = get_active_contracts(symbol, df)
            instrument_map[symbol] = contracts
            # Log only first 5 to prevent console flooding if watchlist is large
            if len(watchlist) <= 5 or symbol in watchlist[:5]:
                logger.info(
                    f"Resolved {symbol} -> Spot: {contracts['spot_key']}, "
                    f"Cur Fut: {contracts['cur_fut_key']} ({contracts['cur_expiry']}), "
                    f"Nxt Fut: {contracts['nxt_fut_key']} ({contracts['nxt_expiry']})"
                )
        except ValueError as e:
            if len(watchlist) <= 5:
                logger.warning(f"Could not resolve contracts for {symbol}: {e}")

    if len(watchlist) > 5:
        logger.info(f"Successfully resolved keys for {len(instrument_map)} / {len(watchlist)} stocks.")

    if not instrument_map:
        logger.error("Failed to resolve active contracts for any watchlisted symbol. Exiting.")
        sys.exit(1)

    # 4. Initialize components
    alert_engine = AlertEngine(config)

    def on_tick(symbol, spot, cur_fut, nxt_fut):
        basis = compute_basis(spot, cur_fut)
        spread = compute_spread(cur_fut, nxt_fut)
        
        logger.debug(
            f"Tick - {symbol}: Spot={spot}, CurFut={cur_fut}, NxtFut={nxt_fut}, "
            f"Basis={basis:.2f}%, Spread={spread:.2f}%"
        )
        
        if alert_engine.should_alert(symbol, basis, spread):
            logger.info(f"🔔 Signal condition met for {symbol}! Sending notifications...")
            try:
                # Resolve list of chat IDs (active DB subscribers + fallback owner ID)
                chat_ids = set()
                if config.TELEGRAM_CHAT_ID:
                    chat_ids.add(str(config.TELEGRAM_CHAT_ID))
                try:
                    active_users = get_registered_users("alerts.db")
                    chat_ids.update(active_users)
                except Exception as db_err:
                    logger.error(f"Error fetching registered telegram users: {db_err}")
                
                if chat_ids:
                    # Dispatch Telegram alert to all subscribers
                    broadcast_telegram(
                        bot_token=config.TELEGRAM_BOT_TOKEN,
                        chat_ids=list(chat_ids),
                        db_path="alerts.db",
                        symbol=symbol,
                        spot=spot,
                        cur_fut=cur_fut,
                        nxt_fut=nxt_fut,
                        basis=basis,
                        spread=spread,
                        cur_expiry=instrument_map[symbol]['cur_expiry'],
                        nxt_expiry=instrument_map[symbol]['nxt_expiry']
                    )
                else:
                    logger.warning("No Telegram chat IDs resolved. Skipping notification dispatch.")

                
                # Write to SQLite log
                log_alert(
                    db_path="alerts.db",
                    symbol=symbol,
                    spot=spot,
                    cur_fut=cur_fut,
                    nxt_fut=nxt_fut,
                    basis=basis,
                    spread=spread,
                    cur_expiry=instrument_map[symbol]['cur_expiry'],
                    nxt_expiry=instrument_map[symbol]['nxt_expiry']
                )
                
                # Update alert engine state (set cooldown and reset breach count)
                alert_engine.record_alert(symbol)
                alert_engine.reset_breach(symbol)
                logger.info(f"Successfully processed alert for {symbol}.")
            except Exception as e:
                logger.error(f"Error executing alert triggers for {symbol}: {e}")

    # 5. Initialize price feed wrapper
    price_feed = PriceFeed(
        access_token=token,
        instrument_map=instrument_map,
        on_tick_callback=on_tick
    )

    # 6. Define scheduler tasks
    def market_open_fn():
        logger.info("Scheduled market open triggered. Connecting feed...")
        price_feed.connect()

    def market_close_fn():
        logger.info("Scheduled market close triggered. Disconnecting feed...")
        price_feed.disconnect()

    # 7. Start connection if within trading hours or if --force is specified
    force_connect = "--force" in sys.argv
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    if force_connect:
        logger.info("Force flag detected. Connecting to live feed immediately (outside trading hours)...")
        price_feed.connect()
    elif is_trading_day() and (time(9, 15) <= now.time() <= time(15, 30)):
        logger.info("Currently within active trading hours. Connecting immediately...")
        price_feed.connect()
    else:
        logger.info("Outside trading hours or market holiday. Waiting for schedule trigger...")

    # 8. Start Telegram Bot Updates Polling Thread
    bot_thread, bot_stop_event = start_telegram_bot_thread("alerts.db", config.TELEGRAM_BOT_TOKEN)

    # 9. Start APScheduler blocking loop
    scheduler = get_scheduler(market_open_fn, market_close_fn)
    logger.info("Starting scheduler loop...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down application...")
        if bot_stop_event:
            bot_stop_event.set()
        try:
            price_feed.disconnect()
        except Exception:
            pass



if __name__ == '__main__':
    main()
