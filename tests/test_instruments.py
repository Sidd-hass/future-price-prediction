import pandas as pd
import pytest
from unittest.mock import patch
from instruments import get_active_contracts, download_instruments

# Sample data mimicking Upstox NSE instruments CSV schema
SAMPLE_DATA = [
    {
        "instrument_key": "NSE_EQ|INE002A01018",
        "exchange_token": "2885",
        "tradingsymbol": "RELIANCE",
        "name": "RELIANCE INDUSTRIES LTD",
        "last_price": "1356.3",
        "expiry": "",
        "strike": "0",
        "tick_size": "0.1",
        "lot_size": "1",
        "instrument_type": "EQUITY",
        "option_type": "",
        "exchange": "NSE_EQ"
    },
    {
        "instrument_key": "NSE_FO|61284",
        "exchange_token": "61284",
        "tradingsymbol": "RELIANCE26JULFUT",
        "name": "RELIANCE INDUSTRIES LTD",
        "last_price": "1370.8",
        "expiry": "2026-07-28",
        "strike": "0.0",
        "tick_size": "0.1",
        "lot_size": "500",
        "instrument_type": "FUTSTK",
        "option_type": "FF",
        "exchange": "NSE_FO"
    },
    {
        "instrument_key": "NSE_FO|62802",
        "exchange_token": "62802",
        "tradingsymbol": "RELIANCE26JUNFUT",
        "name": "RELIANCE INDUSTRIES LTD",
        "last_price": "1363.9",
        "expiry": "2026-06-30",
        "strike": "0.0",
        "tick_size": "0.1",
        "lot_size": "500",
        "instrument_type": "FUTSTK",
        "option_type": "FF",
        "exchange": "NSE_FO"
    },
    {
        "instrument_key": "NSE_FO|58371",
        "exchange_token": "58371",
        "tradingsymbol": "RELIANCE26AUGFUT",
        "name": "RELIANCE INDUSTRIES LTD",
        "last_price": "0",
        "expiry": "2026-08-25",
        "strike": "0.0",
        "tick_size": "0.1",
        "lot_size": "500",
        "instrument_type": "FUTSTK",
        "option_type": "FF",
        "exchange": "NSE_FO"
    }
]


@patch("pandas.read_csv")
def test_download_instruments(mock_read_csv):
    mock_df = pd.DataFrame(SAMPLE_DATA)
    mock_read_csv.return_value = mock_df
    
    # Force removal of cache to trigger download
    if os.path.exists("instruments_cache.csv"):
        os.remove("instruments_cache.csv")
        
    df = download_instruments()
    mock_read_csv.assert_called_once()
    assert len(df) == 4
    
    # Cleanup cached file
    if os.path.exists("instruments_cache.csv"):
        os.remove("instruments_cache.csv")


def test_get_active_contracts_returns_correct_keys():
    df = pd.DataFrame(SAMPLE_DATA)
    contracts = get_active_contracts("RELIANCE", df)
    
    assert contracts["spot_key"] == "NSE_EQ|INE002A01018"
    assert contracts["cur_fut_key"] == "NSE_FO|62802"
    assert contracts["nxt_fut_key"] == "NSE_FO|61284"


def test_get_active_contracts_sorts_by_expiry():
    df = pd.DataFrame(SAMPLE_DATA)
    # The order of contracts in SAMPLE_DATA has July before June futures.
    # get_active_contracts should sort them, so June is current and July is next.
    contracts = get_active_contracts("RELIANCE", df)
    
    assert contracts["cur_expiry"] == "2026-06-30"
    assert contracts["nxt_expiry"] == "2026-07-28"


def test_raises_if_fewer_than_two_futures():
    # Only spot and 1 futures contract
    limited_data = [SAMPLE_DATA[0], SAMPLE_DATA[1]]
    df = pd.DataFrame(limited_data)
    
    with pytest.raises(ValueError) as excinfo:
        get_active_contracts("RELIANCE", df)
    assert "Fewer than 2 active futures found" in str(excinfo.value)
import os
