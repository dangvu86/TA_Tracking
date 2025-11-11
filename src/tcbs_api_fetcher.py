import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional
import requests
import time


@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_tcbs_api_data(ticker: str, days: int = 365) -> Optional[pd.DataFrame]:
    """
    Fetch stock/index data from TCBS API directly

    Args:
        ticker: Stock ticker or index name
        days: Number of days to fetch

    Returns:
        DataFrame with OHLCV data or None if error
    """
    try:
        # Calculate timestamps
        end_timestamp = int(time.time())
        start_timestamp = int(end_timestamp - days * 24 * 60 * 60)

        # VNMIDCAP should not reach here - handled exclusively by Google Sheets
        if ticker == 'VNMIDCAP':
            st.warning(f"VNMIDCAP should use Google Sheets exclusively, not TCBS API")
            return None

        # Build API URL
        url = f"https://apipubaws.tcbs.com.vn/stock-insight/v1/stock/bars-long-term"
        params = {
            'ticker': ticker,
            'type': 'stock',
            'resolution': 'D',
            'from': start_timestamp,
            'to': end_timestamp
        }

        # Add timeout and retry for connection issues
        max_retries = 2
        df = None
        last_error = None

        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()

                data = response.json()

                # Check if data is available
                if 'data' not in data or not data['data']:
                    raise Exception("No data available from TCBS API")

                # Parse response data (list of objects)
                bars = data['data']

                # Convert to DataFrame
                df = pd.DataFrame(bars)

                # Rename columns to match expected format
                column_mapping = {
                    'tradingDate': 'Date',
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                }
                df = df.rename(columns=column_mapping)

                # Convert Date column to datetime
                df['Date'] = pd.to_datetime(df['Date'])

                if df is not None and not df.empty:
                    break  # Success, exit retry loop

            except Exception as retry_error:
                last_error = retry_error
                if attempt < max_retries - 1:
                    time.sleep(1)  # Wait 1 second before retry
                    continue
                else:
                    raise retry_error

        if df is None or df.empty:
            raise last_error if last_error else Exception("No data available")

        # Add missing columns for compatibility
        df['Dividends'] = 0
        df['Stock Splits'] = 0

        # Sort by date and reset index
        df = df.sort_values('Date').reset_index(drop=True)

        return df

    except Exception as e:
        st.warning(f"Error fetching TCBS API data for {ticker}: {str(e)}")
        return None


def is_vietnamese_symbol(ticker: str, exchange: str) -> bool:
    """Check if symbol should use TCBS API (Vietnamese market, excluding VNMIDCAP)"""
    # Vietnamese indices available on TCBS API (VNMIDCAP excluded - uses Google Sheets)
    vn_indices = ['VNINDEX']
    if ticker in vn_indices:
        return True

    # VNMID maps to VNMIDCAP which uses Google Sheets exclusively
    if ticker in ['VNMID', 'VNMIDCAP']:
        return False

    # Vietnamese stock exchanges
    if exchange in ['HOSE', 'HNX', 'UPCOM']:
        return True

    return False


def get_available_vn_indices() -> list:
    """Get list of Vietnamese indices available on TCBS API (VNMIDCAP uses Google Sheets)"""
    return ['VNINDEX']


def format_ticker_for_tcbs(ticker: str) -> str:
    """Format ticker for TCBS API"""
    # Handle special cases
    if ticker == 'VNMID':
        return 'VNMIDCAP'  # Map VNMID to VNMIDCAP

    return ticker


def test_tcbs_connection() -> bool:
    """Test TCBS API connection"""
    try:
        test_df = fetch_tcbs_api_data("VNINDEX", days=5)
        return test_df is not None and not test_df.empty
    except:
        return False
