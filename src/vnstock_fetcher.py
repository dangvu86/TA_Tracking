import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional
from vnstock import Vnstock


@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_vnstock_data(ticker: str, days: int = 365) -> Optional[pd.DataFrame]:
    """
    Fetch stock/index data from vnstock API
    
    Args:
        ticker: Stock ticker or index name
        days: Number of days to fetch
    
    Returns:
        DataFrame with OHLCV data or None if error
    """
    try:
        vnstock = Vnstock()
        
        # Calculate date range
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Determine source based on ticker
        if ticker == 'VNMIDCAP':
            source = 'VCI'  # VNMIDCAP only available on VCI
        else:
            source = 'TCBS'  # VNINDEX and stocks use TCBS
        
        stock_obj = vnstock.stock(symbol=ticker, source=source)
        df = stock_obj.quote.history(start=start_date, end=end_date)
        
        if df is not None and not df.empty:
            # Rename columns to match Yahoo Finance format
            column_mapping = {
                'time': 'Date',
                'open': 'Open',
                'high': 'High',
                'low': 'Low', 
                'close': 'Close',
                'volume': 'Volume'
            }
            
            df = df.rename(columns=column_mapping)
            
            # Ensure Date column is datetime
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
            
            # Add missing columns for compatibility
            if 'Volume' not in df.columns:
                df['Volume'] = 0
                
            # Add dividend and stock split columns (for compatibility)
            df['Dividends'] = 0
            df['Stock Splits'] = 0
            
            # Sort by date and reset index
            df = df.sort_values('Date').reset_index(drop=True)
            
            return df
            
    except Exception as e:
        st.warning(f"Error fetching vnstock data for {ticker}: {str(e)}")
        return None


def is_vietnamese_symbol(ticker: str, exchange: str) -> bool:
    """Check if symbol should use vnstock (Vietnamese market)"""
    # Vietnamese indices available on vnstock
    vn_indices = ['VNINDEX', 'VNMIDCAP', 'VNMID']
    if ticker in vn_indices:
        return True
    
    # Vietnamese stock exchanges
    if exchange in ['HOSE', 'HNX', 'UPCOM']:
        return True
        
    return False


def get_available_vn_indices() -> list:
    """Get list of Vietnamese indices available on vnstock"""
    return ['VNINDEX', 'VNMIDCAP']


def format_ticker_for_vnstock(ticker: str) -> str:
    """Format ticker for vnstock API"""
    # Handle special cases
    if ticker == 'VNMID':
        return 'VNMIDCAP'  # Map VNMID to VNMIDCAP
    
    return ticker


def get_vnstock_source(ticker: str) -> str:
    """Get the correct vnstock source for ticker"""
    if ticker == 'VNMIDCAP':
        return 'VCI'
    else:
        return 'TCBS'


def test_vnstock_connection() -> bool:
    """Test vnstock API connection"""
    try:
        test_df = fetch_vnstock_data("VNINDEX", days=5)
        return test_df is not None and not test_df.empty
    except:
        return False