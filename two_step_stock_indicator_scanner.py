#!/usr/bin/env python
"""
Two-Step Pivot Scanner (Using stock-indicators library)
Step 1: Scans a watchlist of underlying stocks.
Step 2: If a stock breaks above its R3 Pivot on 15m, it fetches its Option Chain.
Step 3: Scans those specific options to see if they ALSO break their own R3 Pivot.
Alerts via Telegram for the options that pass the final criteria.
"""
from openalgo import api
import pandas as pd
import time
from datetime import datetime, timedelta
import os
import requests

# Import the stock-indicators library
from stock_indicators import indicators, Quote
from stock_indicators.indicators.common.enums import PeriodSize, PivotPointType

# Set your API keys and host
api_key = os.getenv('test_key')
host    = os.getenv('HOST_SERVER', 'http://127.0.0.1:5000')

# Telegram settings
telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', 'your_bot_token_here')
telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', 'your_chat_id_here')

if not api_key:
    print("Error: OPENALGO_API_KEY environment variable not set")
    exit(1)

client = api(api_key=api_key, host=host)

WATCHLIST = [
    "AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ADANIENSOL", "ADANIENT", "ADANIPORTS", 
    "ALKEM", "AMBUJACEM", "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", "ASTRAL", "ATUL", "AUBANK", 
    "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BALKRISIND", "BALRAMCHIN", 
    "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", "BERGEPAINT", "BHARATFORG", "BHARTIARTL", "BHEL", 
    "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "BSOFT", "CANBK", "CANFINHOME", "CHAMBLFERT", "CHOLAFIN", 
    "CIPLA", "COALINDIA", "COFORGE", "COLPAL", "CONCOR", "COROMANDEL", "CROMPTON", "CUB", "CUMMINSIND", 
    "DABUR", "DALBHARAT", "DEEPAKNTR", "DIVISLAB", "DIXON", "DLF", "DRREDDY", "EICHERMOT", "ESCORTS", 
    "EXIDEIND", "FEDERALBNK", "GAIL", "GLENMARK", "GMRINFRA", "GNFC", "GODREJCP", "GODREJPROP", "GRANULES", 
    "GRASIM", "GUJGASLTD", "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", 
    "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDEA", 
    "IDFC", "IDFCFIRSTB", "IEX", "IGL", "INDHOTEL", "INDIACEM", "INDIAMART", "INDIGO", "INDUSINDBK", 
    "INDUSTOWER", "INFY", "INTELLECT", "IOC", "IPCALAB", "IRCTC", "ITC", "JINDALSTEL", "JKCEMENT", 
    "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", "L&TFH", "LALPATHLAB", "LAURUSLABS", "LICHSGFIN", "LT", "LTIM", 
    "LTTS", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", "MARICO", "MARUTI", "MCDOWELL-N", "MCX", "METROPOLIS", 
    "MFSL", "MGL", "MOTHERSON", "MPHASIS", "MRF", "MUTHOOTFIN", "NATIONALUM", "NAUKRI", "NAVINFLUOR", 
    "NESTLEIND", "NMDC", "NTPC", "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND", "PEL", "PETRONET", "PFC", 
    "PIDILITIND", "PIIND", "PNB", "POLYCAB", "POWERGRID", "PVRINOX", "RAMCOCEM", "RBLBANK", "RECLTD", 
    "RELIANCE", "SAIL", "SBICARD", "SBILIFE", "SBIN", "SHREECEM", "SHRIRAMFIN", "SIEMENS", "SRF", 
    "SUNPHARMA", "SUNTV", "SYNGENE", "TATACHEM", "TATACOMM", "TATACONSUM", "TATAMOTORS", "TATAPOWER", 
    "TATASTEEL", "TCS", "TECHM", "TITAN", "TORNTPHARM", "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO", "UPL", 
    "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ZYDUSLIFE"
]

interval = "15m"
strike_count = 3  # Check 3 strikes above and below ATM

def send_telegram_alert(message):
    if not telegram_bot_token or not telegram_chat_id:
        print(f"[{datetime.now()}] ALERTS DISABLED (No credentials): \n{message}")
        return
        
    url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    payload = {"chat_id": telegram_chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"[{datetime.now()}] Error sending telegram message: {e}")

def check_r3_breakout(symbol, exchange):
    """Fetches history and checks if the symbol closed above its R3 pivot using stock-indicators."""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    
    try:
        df = client.history(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            start_date=start_date,
            end_date=end_date
        )

        if df is None or df.empty or len(df) < 5:
            return False, None, None

        # Convert DataFrame to list of Quotes for stock-indicators
        quotes = []
        for index, row in df.iterrows():
            # Handle potential timestamp formats
            if 'timestamp' in row:
                dt = pd.to_datetime(row['timestamp'])
            else:
                dt = pd.to_datetime(index)
                
            quotes.append(Quote(
                dt, 
                float(row['open']), 
                float(row['high']), 
                float(row['low']), 
                float(row['close']), 
                float(row['volume'])
            ))

        # Calculate Pivot Points using stock-indicators
        # We calculate Daily pivot points mapped to the 15m quotes
        pivot_results = indicators.get_pivot_points(quotes, PeriodSize.DAY, PivotPointType.STANDARD)
        
        # Check the last completed bar (index -2)
        last_completed_bar_quote = quotes[-2]
        last_completed_bar_pivot = pivot_results[-2]
        
        close_price = last_completed_bar_quote.close
        
        # Properties in python wrapper are generally lower case (e.g. .r3) 
        # but fallback to dictionary access if needed
        try:
            r3_level = last_completed_bar_pivot.r3
        except AttributeError:
            r3_level = last_completed_bar_pivot.R3
        
        # The pivot might be None if there's not enough data to establish a daily pivot
        if r3_level is not None and close_price > r3_level:
            return True, close_price, r3_level
            
    except Exception as e:
        print(f"[{datetime.now()}] Error processing {symbol}: {e}")
        
    return False, None, None

def get_nearest_expiry(underlying, exchange="NSE"):
    try:
        res = client.expiry(symbol=underlying, exchange=exchange)
        if res.get('status') == 'success' and res.get('data'):
            return res['data'][0]
    except Exception as e:
        print(f"[{datetime.now()}] Error getting expiry for {underlying}: {e}")
    return None

def get_options_for_underlying(underlying):
    """Fetches Option symbols for a given underlying stock within +/- 5% of LTP."""
    expiry_date = get_nearest_expiry(underlying)
    if not expiry_date:
        return []

    try:
        # Omitting strike_count to get all strikes
        chain_res = client.optionchain(
            underlying=underlying, 
            exchange="NSE", 
            expiry_date=expiry_date
        )
        
        if chain_res.get('status') != 'success' or 'chain' not in chain_res:
            return []

        underlying_ltp = chain_res.get('underlying_ltp')
        if not underlying_ltp:
            print(f"[{datetime.now()}] Missing underlying_ltp for {underlying}")
            return []

        lower_bound = underlying_ltp * 0.95
        upper_bound = underlying_ltp * 1.05

        options = []
        for strike_data in chain_res['chain']:
            strike = float(strike_data['strike'])
            
            # Filter strikes within 5% up or down from LTP
            if lower_bound <= strike <= upper_bound:
                if 'ce' in strike_data and 'symbol' in strike_data['ce']:
                    options.append(strike_data['ce']['symbol'])
                if 'pe' in strike_data and 'symbol' in strike_data['pe']:
                    options.append(strike_data['pe']['symbol'])
                
        return options
    except Exception as e:
        print(f"[{datetime.now()}] Error fetching option chain for {underlying}: {e}")
        return []

def scan_market():
    print(f"[{datetime.now()}] === STARTING 2-STEP SCAN (stock-indicators) ===")
    
    breakout_stocks = []
    
    # STEP 1: Scan underlying stocks
    print(f"[{datetime.now()}] Step 1: Scanning {len(WATCHLIST)} underlying stocks...")
    for stock in WATCHLIST:
        is_breakout, price, r3 = check_r3_breakout(stock, "NSE")
        if is_breakout:
            print(f"🟢 [STOCK BREAKOUT] {stock} (Close: {price} > R3: {r3:.2f})")
            breakout_stocks.append(stock)
        time.sleep(0.3) # API Rate limit protection
            
    if not breakout_stocks:
        print(f"[{datetime.now()}] No underlying stocks broke R3. Waiting for next cycle.")
        return
        
    print(f"[{datetime.now()}] Step 1 Complete. Found {len(breakout_stocks)} stocks: {', '.join(breakout_stocks)}")
    
    # STEP 2: Fetch options for those specific stocks and scan them
    final_option_alerts = []
    
    print(f"[{datetime.now()}] Step 2: Fetching and scanning options for those {len(breakout_stocks)} stocks...")
    for stock in breakout_stocks:
        options = get_options_for_underlying(stock)
        print(f"Found {len(options)} options for {stock}. Scanning...")
        
        for opt_symbol in options:
            is_breakout, opt_price, opt_r3 = check_r3_breakout(opt_symbol, "NFO")
            if is_breakout:
                msg = f"🔥 *{opt_symbol}*\nClose: *{opt_price}* > R3: *{opt_r3:.2f}*"
                final_option_alerts.append(msg)
                print(f"   => 🟢 [OPTION BREAKOUT] {opt_symbol}")
            time.sleep(0.3) # API Rate limit protection

    # Send a consolidated alert if we found any option breakouts
    if final_option_alerts:
        final_message = f"🎯 *Option Scanner Breakouts (stock-indicators)*\n\n" + "\n\n".join(final_option_alerts)
        send_telegram_alert(final_message)
    else:
        print(f"[{datetime.now()}] Underlying stocks broke out, but none of their options broke R3.")

def main():
    while True:
        scan_market()
        print(f"[{datetime.now()}] === SCAN CYCLE COMPLETE ===\nSleeping for 15 minutes...\n")
        time.sleep(900)  # Sleep for 15 minutes

if __name__ == "__main__":
    main()
