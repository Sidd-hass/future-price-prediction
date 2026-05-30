import os
import gzip
import io
import requests
import pandas as pd

def download_instruments() -> pd.DataFrame:
    """
    Downloads NSE F&O instrument CSV from Upstox:
    https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz
    Returns a pandas DataFrame cached to instruments_cache.csv
    """
    cache_path = "instruments_cache.csv"
    if os.path.exists(cache_path):
        return pd.read_csv(cache_path)
    
    url = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    decompressed = gzip.decompress(response.content)
    df = pd.read_csv(io.BytesIO(decompressed))
    df.to_csv(cache_path, index=False)
    return df


def get_active_contracts(symbol: str, df: pd.DataFrame) -> dict:
    """
    Given a stock symbol and the instruments DataFrame:
    - Finds the EQ (spot) instrument key from NSE_EQ segment
    - Finds futures (instrument_type == FUT) sorted by expiry date
    - Returns dict: {spot_key, cur_fut_key, nxt_fut_key, 
                     cur_expiry, nxt_expiry}
    - Raises ValueError if fewer than 2 active futures found
    """
    segment_col = 'exchange' if 'exchange' in df.columns else ('segment' if 'segment' in df.columns else None)
    if not segment_col:
        raise ValueError("Could not find segment/exchange column in instrument DataFrame.")

    # 1. Find spot EQ instrument key
    spot_mask = (df[segment_col] == 'NSE_EQ') & (df['tradingsymbol'] == symbol)
    spot_df = df[spot_mask]
    if spot_df.empty:
        raise ValueError(f"Spot instrument not found for symbol: {symbol}")
    
    spot_row = spot_df.iloc[0]
    spot_key = spot_row['instrument_key']
    spot_name = spot_row['name']

    # 2. Find futures contracts
    # Look for exchange == 'NSE_FO' and instrument_type starting with 'FUT'
    # and corporate name matching the spot name (or symbol matching tradingsymbol)
    fut_mask = (
        (df[segment_col] == 'NSE_FO') &
        (df['name'] == spot_name) &
        (df['instrument_type'].astype(str).str.startswith('FUT', na=False))
    )
    fut_df = df[fut_mask].copy()

    # Fallback to tradingsymbol match if name matches are empty or insufficient
    if len(fut_df) < 2:
        fut_mask_alt = (
            (df[segment_col] == 'NSE_FO') &
            (df['tradingsymbol'].astype(str).str.startswith(symbol, na=False)) &
            (df['tradingsymbol'].astype(str).str.endswith('FUT', na=False)) &
            (df['instrument_type'].astype(str).str.startswith('FUT', na=False))
        )
        fut_df = df[fut_mask_alt].copy()

    if len(fut_df) < 2:
        raise ValueError(f"Fewer than 2 active futures found for symbol: {symbol}")

    # Convert expiry to datetime for proper chronological sorting
    fut_df['expiry_dt'] = pd.to_datetime(fut_df['expiry'])
    fut_df = fut_df.sort_values(by='expiry_dt')

    cur_fut = fut_df.iloc[0]
    nxt_fut = fut_df.iloc[1]

    return {
        "spot_key": spot_key,
        "cur_fut_key": cur_fut['instrument_key'],
        "nxt_fut_key": nxt_fut['instrument_key'],
        "cur_expiry": str(cur_fut['expiry']),
        "nxt_expiry": str(nxt_fut['expiry'])
    }
