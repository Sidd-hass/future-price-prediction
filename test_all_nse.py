import os
import sys
import requests
import pandas as pd
from urllib.parse import quote

# 1. Load config and helper functions
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import config
from auth_server import load_token
from instruments import download_instruments, get_active_contracts
from calculator import compute_basis, compute_spread
from alert_logic import AlertEngine
from notifier import send_telegram, broadcast_telegram
from logger import get_registered_users

def main():
    print("\n" + "=" * 80)
    # Use double-braces to avoid formatting confusion if any, but regular string is fine
    print("  FUTURES-ALERT · FULL NSE F&O SEGMENT SCANNER")
    print("=" * 80 + "\n")

    # 2. Load access token
    try:
        token = load_token("token.txt")
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    # 3. Resolve F&O stock list
    print("📥 Fetching and parsing instruments list...")
    df = download_instruments()

    # We identify F&O stocks by filtering exchange == NSE_FO and instrument_type == FUTSTK
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
    print(f"✅ Found {len(watchlist)} F&O stock symbols in NSE.")

    # 4. Resolve contracts (keys) for all stocks
    print("🔍 Resolving spot and futures contracts for all stocks (this takes ~1 second)...")
    instrument_map = {}
    all_keys = []
    key_to_symbol = {}

    for symbol in watchlist:
        try:
            contracts = get_active_contracts(symbol, df)
            instrument_map[symbol] = contracts
            
            s_key = contracts['spot_key']
            c_key = contracts['cur_fut_key']
            n_key = contracts['nxt_fut_key']
            
            all_keys.extend([s_key, c_key, n_key])
            key_to_symbol[s_key] = symbol
            key_to_symbol[c_key] = symbol
            key_to_symbol[n_key] = symbol
        except Exception:
            # Skip unresolved stocks (e.g. if contract name mismatch)
            pass

    print(f"✅ Resolved keys for {len(instrument_map)} stocks. Total instrument keys: {len(all_keys)}")

    # 5. Fetch LTP for all keys using the Upstox REST API in chunks
    print(f"🌐 Fetching LTP from Upstox REST API in chunks (max 300 keys per request)...")
    chunk_size = 300
    prices = {}

    # Split keys into chunks of 300
    chunks = [all_keys[i:i + chunk_size] for i in range(0, len(all_keys), chunk_size)]
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

    for idx, chunk in enumerate(chunks):
        keys_str = ",".join(chunk)
        url = f"https://api.upstox.com/v2/market-quote/ltp?instrument_key={quote(keys_str)}"
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 401:
                print("❌ Unauthorized: Your token.txt may have expired. Please rerun auth_server.py first.")
                sys.exit(1)
            response.raise_for_status()
            resp_json = response.json()
            
            data = resp_json.get("data", {})
            for key, details in data.items():
                if details and "last_price" in details:
                    inst_token = details.get("instrument_token")
                    if inst_token:
                        prices[inst_token] = float(details["last_price"])
        except Exception as e:
            print(f"⚠️ Error fetching chunk {idx + 1}: {e}")

    print(f"✅ Successfully fetched prices for {len(prices)} / {len(all_keys)} keys.")

    # 6. Analyze basis and spread for each stock
    results = []
    alerts_triggered = []
    engine = AlertEngine(config)

    for symbol, contracts in instrument_map.items():
        s_key = contracts['spot_key']
        c_key = contracts['cur_fut_key']
        n_key = contracts['nxt_fut_key']
        
        spot = prices.get(s_key)
        cur_fut = prices.get(c_key)
        nxt_fut = prices.get(n_key)
        
        if spot is not None and cur_fut is not None and nxt_fut is not None and spot > 0 and cur_fut > 0:
            basis = compute_basis(spot, cur_fut)
            spread = compute_spread(cur_fut, nxt_fut)
            is_triggered = engine.check_conditions(basis, spread)
            
            results.append({
                "Symbol": symbol,
                "Spot": spot,
                "CurFut": cur_fut,
                "NxtFut": nxt_fut,
                "Basis%": basis,
                "Spread%": spread,
                "Triggered": "YES" if is_triggered else "NO"
            })
            
            if is_triggered:
                alerts_triggered.append((symbol, spot, cur_fut, nxt_fut, basis, spread, contracts))

    # Create a DataFrame to sort and display results
    results_df = pd.DataFrame(results)

    if not results_df.empty:
        # Sort by Basis% descending to see which stocks are trading at the highest discount to spot
        sorted_df = results_df.sort_values(by="Basis%", ascending=False)
        print("\n" + "=" * 80)
        print("  TOP 15 STOCKS WITH HIGHEST BASIS DISCOUNT (CURRENT / LAST CLOSED PRICES)")
        print("=" * 80)
        print(sorted_df.head(15).to_string(index=False))
        print("=" * 80 + "\n")
    else:
        print("❌ No valid pricing data could be analyzed.")

    # 7. Print real triggers
    if alerts_triggered:
        print(f"🚨 FOUND {len(alerts_triggered)} STOCK(S) MEETING ALERT CONDITIONS IN THE REAL MARKET:")
        for sym, spot, cur_fut, nxt_fut, basis, spread, contracts in alerts_triggered:
            print(f"   • {sym}: Basis={basis:.2f}% (threshold > {config.BASIS_THRESHOLD}%), Spread={spread:.4f}% (threshold [{config.SPREAD_MIN}%, {config.SPREAD_MAX}%])")
            # Trigger real Telegram alert
            print(f"   ✉️ Sending real Telegram alert for {sym}...")
            # Resolve list of chat IDs (active DB subscribers + fallback owner ID)
            chat_ids = set()
            if config.TELEGRAM_CHAT_ID:
                chat_ids.add(str(config.TELEGRAM_CHAT_ID))
            try:
                active_users = get_registered_users("alerts.db")
                chat_ids.update(active_users)
            except Exception as db_err:
                print(f"   ⚠️ Error fetching registered telegram users: {db_err}")
                
            if chat_ids:
                try:
                    broadcast_telegram(
                        bot_token=config.TELEGRAM_BOT_TOKEN,
                        chat_ids=list(chat_ids),
                        db_path="alerts.db",
                        symbol=sym,
                        spot=spot,
                        cur_fut=cur_fut,
                        nxt_fut=nxt_fut,
                        basis=basis,
                        spread=spread,
                        cur_expiry=contracts['cur_expiry'],
                        nxt_expiry=contracts['nxt_expiry']
                    )
                    print(f"   ✅ Telegram alerts broadcasted successfully to {len(chat_ids)} users.")
                except Exception as e:
                    print(f"   ❌ Telegram broadcast failed: {e}")
            else:
                print("   ⚠️ No Telegram chat IDs resolved. Skipping notification dispatch.")
    else:
        print("ℹ️ No stocks in the real F&O segment currently meet the alert criteria.")
        print(f"   (Basis discount > {config.BASIS_THRESHOLD}% and Calendar spread between {config.SPREAD_MIN}% and {config.SPREAD_MAX}%)\n")
        
        # 8. Run simulated mock trigger to verify the alert & Telegram dispatch pipeline
        print("=" * 80)
        print("  SIMULATING MOCK ALERT FOR TESTING TELEGRAM NOTIFICATION ENGINE")
        print("=" * 80)
        
        # Choose a stock to mock (e.g. RELIANCE)
        mock_sym = "RELIANCE"
        if mock_sym in instrument_map:
            contracts = instrument_map[mock_sym]
            mock_spot = 1356.30
            mock_cur = 1325.00
            mock_nxt = 1326.30
            mock_basis = compute_basis(mock_spot, mock_cur)
            mock_spread = compute_spread(mock_cur, mock_nxt)
            
            print(f"\n   Simulating mock conditions for {mock_sym}:")
            print(f"   Spot = ₹{mock_spot}")
            print(f"   Cur Fut = ₹{mock_cur} (Basis = {mock_basis:.2f}%)")
            print(f"   Nxt Fut = ₹{mock_nxt} (Spread = {mock_spread:.4f}%)")
            
            print(f"   ✉️ Dispatching test Telegram alert...")
            # Resolve list of chat IDs (active DB subscribers + fallback owner ID)
            chat_ids = set()
            if config.TELEGRAM_CHAT_ID:
                chat_ids.add(str(config.TELEGRAM_CHAT_ID))
            try:
                active_users = get_registered_users("alerts.db")
                chat_ids.update(active_users)
            except Exception as db_err:
                print(f"   ⚠️ Error fetching registered telegram users: {db_err}")
                
            if chat_ids:
                try:
                    broadcast_telegram(
                        bot_token=config.TELEGRAM_BOT_TOKEN,
                        chat_ids=list(chat_ids),
                        db_path="alerts.db",
                        symbol=mock_sym,
                        spot=mock_spot,
                        cur_fut=mock_cur,
                        nxt_fut=mock_nxt,
                        basis=mock_basis,
                        spread=mock_spread,
                        cur_expiry=contracts['cur_expiry'],
                        nxt_expiry=contracts['nxt_expiry']
                    )
                    print(f"   ✅ Test Telegram alerts broadcasted successfully to {len(chat_ids)} users.")
                except Exception as e:
                    print(f"   ❌ Test Telegram broadcast failed: {e}")
            else:
                print("   ⚠️ No Telegram chat IDs resolved. Skipping notification dispatch.")
        print("=" * 80 + "\n")

if __name__ == '__main__':
    main()
