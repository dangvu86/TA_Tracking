import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime, timedelta
import numpy as np

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.stock_loader import load_stock_list
from src.data_fetcher import fetch_stock_data, get_last_trading_date
from src.indicators.calculator import calculate_all_indicators, get_latest_indicators
from src.indicators.signals import evaluate_all_signals

st.set_page_config(
    page_title="Technical Analysis Summary",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown("""
<div class="main-header">
    <h1>📈 Technical Analysis Summary</h1>
</div>
""", unsafe_allow_html=True)


# Date selection
st.subheader("📅 Analysis Date")
selected_date = st.date_input(
    "Select Analysis Date",
    value=get_last_trading_date().date(),
    max_value=datetime.now().date()
)

# Analysis and display
try:
    from src.utils.signal_counter import count_signals, calculate_price_change, calculate_ratings
    
    # Load stock list
    stock_df = load_stock_list()
    
    if st.button("🔄 Run Analysis") or 'analysis_results' not in st.session_state:
        
        # Initialize results
        results = []
        
        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_stocks = len(stock_df)
        
        for idx, (_, row) in enumerate(stock_df.iterrows()):
            ticker = row['Ticker']
            sector = row['Sector']
            exchange = row['Exchange']
            
            status_text.text(f"Analyzing {ticker}... ({idx+1}/{total_stocks})")
            progress_bar.progress((idx + 1) / total_stocks)
            
            try:
                # Ensure selected_date is a date object and convert to datetime
                if isinstance(selected_date, str):
                    selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d')
                else:
                    selected_date_dt = datetime.combine(selected_date, datetime.min.time())
                
                # Fetch data
                df = fetch_stock_data(ticker, selected_date_dt, exchange=exchange)
                
                if df is None or df.empty:
                    # Add row with no data
                    result_row = {
                        'Sector': sector,
                        'Ticker': ticker,
                        'Price': np.nan,
                        '% Change': np.nan,
                        'Osc Buy': 0,
                        'Osc Sell': 0,
                        'MA Buy': 0,
                        'MA Sell': 0
                    }
                    # Add empty signals
                    from src.utils.signal_counter import OSCILLATOR_SIGNALS, MA_SIGNALS
                    for signal_name in OSCILLATOR_SIGNALS + MA_SIGNALS:
                        result_row[signal_name] = 'N/A'
                    
                    results.append(result_row)
                    continue
                
                # Calculate indicators
                df_with_indicators = calculate_all_indicators(df)
                indicators = get_latest_indicators(df_with_indicators, pd.Timestamp(selected_date_dt))
                
                if not indicators:
                    # Add row with no data
                    result_row = {
                        'Sector': sector,
                        'Ticker': ticker,
                        'Price': np.nan,
                        '% Change': np.nan,
                        'Osc Buy': 0,
                        'Osc Sell': 0,
                        'MA Buy': 0,
                        'MA Sell': 0
                    }
                    # Add empty signals
                    for signal_name in OSCILLATOR_SIGNALS + MA_SIGNALS:
                        result_row[signal_name] = 'N/A'
                    
                    results.append(result_row)
                    continue
                
                # Evaluate signals
                signals = evaluate_all_signals(indicators)
                
                # Count signals
                osc_buy, osc_sell, ma_buy, ma_sell = count_signals(signals)
                
                # Calculate ratings
                rating1, rating2 = calculate_ratings(osc_buy, osc_sell, ma_buy, ma_sell)
                
                # Get price info
                current_price = indicators.get('Price', np.nan)
                
                # Calculate price change (using previous day's close)
                df_sorted = df_with_indicators.sort_values('Date')
                if len(df_sorted) >= 2:
                    prev_price = df_sorted.iloc[-2]['Close'] if len(df_sorted) > 1 else current_price
                else:
                    prev_price = current_price
                
                price_change = calculate_price_change(current_price, prev_price)
                
                # Create result row with basic info
                result_row = {
                    'Sector': sector,
                    'Ticker': ticker,
                    'Price': current_price,
                    '% Change': price_change,
                    'Osc Buy': osc_buy,
                    'Osc Sell': osc_sell,
                    'MA Buy': ma_buy,
                    'MA Sell': ma_sell,
                    'MA5': indicators.get('SMA_5', np.nan),
                    'Close_vs_MA5': indicators.get('Close_vs_MA5', np.nan),
                    'Close_vs_MA10': indicators.get('Close_vs_MA10', np.nan),
                    'Close_vs_MA20': indicators.get('Close_vs_MA20', np.nan),
                    'Close_vs_MA50': indicators.get('Close_vs_MA50', np.nan),
                    'Close_vs_MA200': indicators.get('Close_vs_MA200', np.nan),
                    'STRENGTH_ST': indicators.get('STRENGTH_ST', np.nan),
                    'STRENGTH_LT': indicators.get('STRENGTH_LT', np.nan),
                    'Rating_1': rating1,
                    'Rating_2': rating2,
                    'MA50_GT_MA200': 'Yes' if indicators.get('MA50_GT_MA200', False) else 'No'
                }
                
                # Add all signal details
                result_row.update(signals)
                
                # Add all indicator values (exclude duplicates already in result_row)
                for key, value in indicators.items():
                    if key not in result_row:
                        result_row[key] = value
                
                results.append(result_row)
                
            except Exception as e:
                st.warning(f"Error analyzing {ticker}: {str(e)}")
                # Add row with error
                result_row = {
                    'Sector': sector,
                    'Ticker': ticker,
                    'Price': np.nan,
                    '% Change': np.nan,
                    'Osc Buy': 0,
                    'Osc Sell': 0,
                    'MA Buy': 0,
                    'MA Sell': 0
                }
                # Add empty signals
                for signal_name in OSCILLATOR_SIGNALS + MA_SIGNALS:
                    result_row[signal_name] = 'Error'
                
                results.append(result_row)
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Store results
        st.session_state.analysis_results = pd.DataFrame(results)
    
    # Display results
    if 'analysis_results' in st.session_state:
        df_results = st.session_state.analysis_results
        
        st.subheader("📊 Analysis Results")
        
        # Organize columns for better display
        basic_cols = ['Sector', 'Ticker', 'Price', '% Change', 'Osc Buy', 'Osc Sell', 'MA Buy', 'MA Sell']
        new_cols = ['MA5', 'Close_vs_MA5', 'Close_vs_MA10', 'Close_vs_MA20', 'Close_vs_MA50', 'Close_vs_MA200', 
                   'STRENGTH_ST', 'STRENGTH_LT', 'Rating_1', 'Rating_2', 'MA50_GT_MA200']
        
        # Get all signal columns
        from src.utils.signal_counter import OSCILLATOR_SIGNALS, MA_SIGNALS
        signal_cols = OSCILLATOR_SIGNALS + MA_SIGNALS
        
        # Define indicator columns in logical groups
        ichimoku_cols = ['Ichimoku_Base', 'Ichimoku_Conversion', 'Ichimoku_A', 'Ichimoku_B']
        sma_cols = [f'SMA_{p}' for p in [5, 10, 20, 30, 50, 100, 200]]
        ema_cols = [f'EMA_{p}' for p in [10, 13, 20, 30, 50, 100, 200]]
        other_ma_cols = ['VWMA_20', 'Hull_MA_9']
        
        oscillator_cols = ['RSI_14', 'Stoch_K', 'Stoch_D', 'CCI_20', 'ADX_14', 'AO', 'Momentum_10', 
                          'MACD', 'MACD_Signal', 'StochRSI_K', 'StochRSI_D', 'Williams_R', 
                          'UO', 'Bull_Power', 'Bear_Power', 'DMI_Positive', 'DMI_Negative']
        
        price_cols = ['High', 'Low']
        prev_cols = ['RSI_Prev', 'CCI_Prev', 'ADX_Prev', 'Momentum_Prev', 'Williams_R_Prev', 
                    'Bull_Power_Prev', 'Bear_Power_Prev', 'EMA_13_Prev', 'AO_Prev']
        
        # Filter available columns
        available_signal_cols = [col for col in signal_cols if col in df_results.columns]
        available_ichimoku = [col for col in ichimoku_cols if col in df_results.columns]
        available_sma = [col for col in sma_cols if col in df_results.columns]
        available_ema = [col for col in ema_cols if col in df_results.columns]
        available_other_ma = [col for col in other_ma_cols if col in df_results.columns]
        available_osc = [col for col in oscillator_cols if col in df_results.columns]
        available_price = [col for col in price_cols if col in df_results.columns]
        available_prev = [col for col in prev_cols if col in df_results.columns]
        
        # Filter new columns that exist
        available_new_cols = [col for col in new_cols if col in df_results.columns]
        
        # Order: Basic info -> New Columns -> Signals -> Indicators (grouped logically)
        column_order = (basic_cols + available_new_cols + available_signal_cols + 
                       available_ichimoku + available_sma + available_ema + available_other_ma + 
                       available_osc + available_price + available_prev)
        
        # Create ordered dataframe with available columns only
        available_columns = [col for col in column_order if col in df_results.columns]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_columns = []
        for col in available_columns:
            if col not in seen:
                unique_columns.append(col)
                seen.add(col)
        
        display_df = df_results[unique_columns].copy()
        
        # Format numeric columns (add new numeric columns to format list)
        numeric_new_cols = ['MA5', 'Close_vs_MA5', 'Close_vs_MA10', 'Close_vs_MA20', 'Close_vs_MA50', 
                           'Close_vs_MA200', 'STRENGTH_ST', 'STRENGTH_LT']
        available_numeric_new_cols = [col for col in numeric_new_cols if col in df_results.columns]
        
        numeric_cols = (available_ichimoku + available_sma + available_ema + available_other_ma + 
                       available_osc + available_price + available_prev + available_numeric_new_cols)
        
        # Format price and % change
        def format_price(x):
            try:
                return f"{float(x):.2f}" if pd.notna(x) and isinstance(x, (int, float)) else "N/A"
            except:
                return "N/A"
        
        def format_change(x):
            try:
                return f"{float(x):+.2f}%" if pd.notna(x) and isinstance(x, (int, float)) else "N/A"
            except:
                return "N/A"
        
        if 'Price' in display_df.columns:
            display_df['Price'] = display_df['Price'].apply(format_price)
        if '% Change' in display_df.columns:
            display_df['% Change'] = display_df['% Change'].apply(format_change)
        
        # Format all numeric indicator columns
        def format_numeric(x):
            try:
                if pd.isna(x):
                    return "N/A"
                elif isinstance(x, (int, float)):
                    return f"{float(x):.4f}"
                else:
                    return str(x)
            except:
                return str(x)
        
        for col in numeric_cols:
            if col in display_df.columns:
                display_df[col] = display_df[col].apply(format_numeric)
        
        # Style the dataframe for signal colors
        def style_signals(val):
            if val == 'Buy':
                return 'background-color: #d4edda; color: #155724'  # Green
            elif val == 'Sell':
                return 'background-color: #f8d7da; color: #721c24'  # Red  
            elif val == 'Neutral':
                return 'background-color: #fff3cd; color: #856404'  # Yellow
            else:
                return ''
        
        # Apply styling only to signal columns that exist in display_df
        signal_cols_in_df = [col for col in available_signal_cols if col in display_df.columns]
        
        if signal_cols_in_df:
            styled_df = display_df.style.applymap(
                style_signals, 
                subset=signal_cols_in_df
            )
        else:
            styled_df = display_df
        
        # Display table
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Summary statistics
        st.subheader("📈 Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_osc_buy = df_results['Osc Buy'].mean()
            st.metric("Avg Osc Buy", f"{avg_osc_buy:.1f}")
        
        with col2:
            avg_osc_sell = df_results['Osc Sell'].mean()
            st.metric("Avg Osc Sell", f"{avg_osc_sell:.1f}")
        
        with col3:
            avg_ma_buy = df_results['MA Buy'].mean()
            st.metric("Avg MA Buy", f"{avg_ma_buy:.1f}")
        
        with col4:
            avg_ma_sell = df_results['MA Sell'].mean()
            st.metric("Avg MA Sell", f"{avg_ma_sell:.1f}")

except Exception as e:
    st.error(f"Error during analysis: {str(e)}")