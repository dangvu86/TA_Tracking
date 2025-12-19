"""
Google Drive Stock Data Fetcher

Fetches Vietnamese stock data from Google Drive CSV files.
Data covers HOSE, HNX, and UPCOM exchanges.
"""

import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional
import requests
from io import StringIO


# Google Drive file IDs containing stock data
GDRIVE_FILES = [
    "1E0BDythcdIdGrIYdbJCNB0DxPHJ-njzc",  # 100 HOSE stocks (Group 1)
    "1cb9Ef1IDyArlmguRZ5u63tCcxR57KEfA",  # 100 HOSE stocks (Group 2)
    "1XPZKnRDklQ1DOdVgncn71SLg1pfisQtV",  # 100 HOSE stocks (Group 3)
    "1op_GzDUtbcXOJOMkI2K-0AU9cF4m8J1S",  # 94 HOSE stocks (Group 4)
    "1JE7XKfdM4QnI6nYNFriFShU3mSWG5_Rj",  # 8 HNX/UPCOM stocks
]


@st.cache_data(ttl=1800)  # Cache for 30 minutes
def _load_gdrive_file(file_id: str) -> Optional[pd.DataFrame]:
    """
    Load a single Google Drive CSV file.
    
    Args:
        file_id: Google Drive file ID
        
    Returns:
        DataFrame with stock data or None if error
    """
    try:
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        df = pd.read_csv(StringIO(response.text))
        
        # Ensure required columns exist
        required_cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            return None
            
        return df
        
    except Exception as e:
        st.warning(f"Error loading Google Drive file {file_id[:8]}...: {str(e)}")
        return None


@st.cache_data(ttl=1800)  # Cache for 30 minutes
def _get_all_gdrive_data() -> Optional[pd.DataFrame]:
    """
    Load and combine all Google Drive stock data files.
    
    Returns:
        Combined DataFrame with all stock data
    """
    all_dfs = []
    
    for file_id in GDRIVE_FILES:
        df = _load_gdrive_file(file_id)
        if df is not None and not df.empty:
            all_dfs.append(df)
    
    if not all_dfs:
        return None
        
    # Combine all dataframes
    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    # Convert date column to datetime
    combined_df['date'] = pd.to_datetime(combined_df['date'])
    
    return combined_df


@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_gdrive_stock_data(ticker: str, days: int = 365) -> Optional[pd.DataFrame]:
    """
    Fetch stock data for a specific ticker from Google Drive files.
    
    Args:
        ticker: Stock ticker symbol
        days: Number of days of history to return
        
    Returns:
        DataFrame with OHLCV data or None if not found
    """
    try:
        # Get all data
        all_data = _get_all_gdrive_data()
        
        if all_data is None or all_data.empty:
            return None
        
        # Filter for the specific ticker
        ticker_data = all_data[all_data['symbol'] == ticker.upper()].copy()
        
        if ticker_data.empty:
            return None
        
        # Sort by date
        ticker_data = ticker_data.sort_values('date')
        
        # Filter to requested number of days
        end_date = ticker_data['date'].max()
        start_date = end_date - timedelta(days=days)
        ticker_data = ticker_data[ticker_data['date'] >= start_date]
        
        # Rename columns to match expected format
        ticker_data = ticker_data.rename(columns={
            'date': 'Date',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        })
        
        # Select and order columns
        ticker_data = ticker_data[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
        
        # Convert prices from thousands to VND (Google Drive has prices like 28.40, we need 28400)
        price_cols = ['Open', 'High', 'Low', 'Close']
        for col in price_cols:
            ticker_data[col] = ticker_data[col] * 1000
        
        # Add missing columns for compatibility
        ticker_data['Dividends'] = 0
        ticker_data['Stock Splits'] = 0
        
        # Reset index
        ticker_data = ticker_data.reset_index(drop=True)
        
        return ticker_data
        
    except Exception as e:
        st.warning(f"Error fetching Google Drive data for {ticker}: {str(e)}")
        return None


def get_available_gdrive_tickers() -> list:
    """
    Get list of all tickers available in Google Drive files.
    
    Returns:
        List of ticker symbols
    """
    try:
        all_data = _get_all_gdrive_data()
        if all_data is not None and not all_data.empty:
            return sorted(all_data['symbol'].unique().tolist())
        return []
    except:
        return []


def is_ticker_in_gdrive(ticker: str) -> bool:
    """
    Check if a ticker is available in Google Drive data.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        True if ticker is available
    """
    try:
        all_data = _get_all_gdrive_data()
        if all_data is not None and not all_data.empty:
            return ticker.upper() in all_data['symbol'].values
        return False
    except:
        return False


def test_gdrive_connection() -> bool:
    """Test Google Drive data connection."""
    try:
        # Try to load the first file
        df = _load_gdrive_file(GDRIVE_FILES[0])
        return df is not None and not df.empty
    except:
        return False


@st.cache_data(ttl=1800)  # Cache for 30 minutes
def get_latest_data_date() -> Optional[datetime]:
    """
    Get the latest date available in Google Drive data files.
    
    This is useful for setting the default date in the app,
    since Google Drive files are updated at end of day.
    
    Returns:
        datetime of the latest data date, or None if error
    """
    try:
        all_data = _get_all_gdrive_data()
        
        if all_data is not None and not all_data.empty:
            latest_date = all_data['date'].max()
            # Convert to datetime if it's a Timestamp
            if hasattr(latest_date, 'to_pydatetime'):
                return latest_date.to_pydatetime()
            return latest_date
        return None
    except Exception as e:
        st.warning(f"Error getting latest data date: {str(e)}")
        return None
