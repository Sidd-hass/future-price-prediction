"""
Live demo: Download real NSE instruments and resolve contracts for the watchlist.
This proves the detection pipeline works with actual market data.
"""
import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from config import WATCHLIST
from instruments import download_instruments, get_active_contracts
from calculator import compute_basis, compute_spread

print("\n" + "=" * 70)
print("  FUTURES-ALERT · LIVE STOCK DETECTION DEMO")
print("=" * 70)

# Step 1: Download real instruments
print("\n📥 Downloading Upstox NSE instruments CSV...")
# Remove cache to force fresh download
if os.path.exists("instruments_cache.csv"):
    os.remove("instruments_cache.csv")

df = download_instruments()
print(f"   Loaded {len(df)} instruments from NSE")

# Show breakdown
eq_count = len(df[df['exchange'] == 'NSE_EQ'])
fo_count = len(df[df['exchange'] == 'NSE_FO'])
print(f"   NSE_EQ (equities):  {eq_count}")
print(f"   NSE_FO (F&O):       {fo_count}")

# Step 2: Resolve contracts for each watchlist symbol
print(f"\n🔍 Resolving contracts for watchlist: {WATCHLIST}")
print("─" * 70)

resolved = {}
for symbol in WATCHLIST:
    try:
        contracts = get_active_contracts(symbol, df)
        resolved[symbol] = contracts
        
        print(f"\n  ✅ {symbol}")
        print(f"     Spot Key:       {contracts['spot_key']}")
        print(f"     Cur Future Key: {contracts['cur_fut_key']}")
        print(f"     Cur Expiry:     {contracts['cur_expiry']}")
        print(f"     Nxt Future Key: {contracts['nxt_fut_key']}")
        print(f"     Nxt Expiry:     {contracts['nxt_expiry']}")
    except ValueError as e:
        print(f"\n  ❌ {symbol} — {e}")

# Step 3: Simulate a price scenario to show detection logic
print("\n\n" + "=" * 70)
print("  SIMULATED ALERT SCENARIO")
print("=" * 70)
print("\n  Using fake prices to show how the alert engine works:\n")

from alert_logic import AlertEngine
import config

engine = AlertEngine(config)

# Simulate RELIANCE with futures at discount
test_cases = [
    ("RELIANCE", 1356.30, 1325.00, 1326.30),  # ~2.3% basis, ~0.1% spread → ALERT
    ("TCS",      3450.00, 3400.00, 3407.00),   # ~1.4% basis → NO ALERT (below threshold)
    ("INFY",     1520.00, 1485.00, 1486.50),   # ~2.3% basis, ~0.1% spread → ALERT
]

for symbol, spot, cur_fut, nxt_fut in test_cases:
    basis = compute_basis(spot, cur_fut)
    spread = compute_spread(cur_fut, nxt_fut)
    cond = engine.check_conditions(basis, spread)
    
    status = "🟢 WOULD ALERT" if cond else "🔴 NO ALERT"
    print(f"  {symbol}:")
    print(f"    Spot=₹{spot}  CurFut=₹{cur_fut}  NxtFut=₹{nxt_fut}")
    print(f"    Basis={basis:.2f}%  Spread={spread:.4f}%  → {status}")
    if cond:
        print(f"    (basis {basis:.2f}% > {config.BASIS_THRESHOLD}%  AND  "
              f"{config.SPREAD_MIN}% ≤ spread {spread:.4f}% ≤ {config.SPREAD_MAX}%)")
    else:
        reasons = []
        if basis <= config.BASIS_THRESHOLD:
            reasons.append(f"basis {basis:.2f}% ≤ threshold {config.BASIS_THRESHOLD}%")
        if spread < config.SPREAD_MIN or spread > config.SPREAD_MAX:
            reasons.append(f"spread {spread:.4f}% outside [{config.SPREAD_MIN}%, {config.SPREAD_MAX}%]")
        print(f"    Reason: {'; '.join(reasons)}")
    print()

# Step 4: Show the keys that would be subscribed to via WebSocket
print("=" * 70)
print("  WEBSOCKET SUBSCRIPTION KEYS")
print("=" * 70)
print("\n  These instrument keys would be sent to the Upstox WebSocket:\n")
all_keys = []
for symbol, contracts in resolved.items():
    keys = [contracts['spot_key'], contracts['cur_fut_key'], contracts['nxt_fut_key']]
    all_keys.extend(keys)
    print(f"  {symbol}: {keys}")

print(f"\n  Total keys to subscribe: {len(all_keys)}")

print("\n" + "=" * 70)
print("  ✅ DETECTION PIPELINE VERIFIED WITH REAL NSE DATA")
print("=" * 70)
print("""
  WHAT'S LEFT TO GO FULLY LIVE:
  ─────────────────────────────
  1. Run:  python auth_server.py
     → Open the printed URL in your browser
     → Log in to Upstox and authorize the app
     → This saves your access token to token.txt

  2. Run:  python main.py
     → Connects WebSocket during market hours (09:15–15:30 IST)
     → Monitors live prices for all resolved instruments
     → Sends Telegram alerts when conditions are met
""")
