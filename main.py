import streamlit as st
import pandas as pd
import os
import sys
from datetime import datetime, timedelta
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode, JsCode

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
    
    # Initialize session state if not exists
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
        st.session_state.last_analysis_date = None
        st.session_state.first_load = True
    
    # Show refresh button and data status
    col_btn, col_status = st.columns([1, 3])
    with col_btn:
        refresh_clicked = st.button("🔄 Refresh Data")
    
    with col_status:
        if st.session_state.analysis_results is not None:
            if st.session_state.last_analysis_date != selected_date:
                st.warning(f"📊 Data loaded for: {st.session_state.last_analysis_date} | Selected: {selected_date} - Click Refresh to update")
            else:
                st.success(f"✅ Data loaded for: {st.session_state.last_analysis_date}")
        else:
            st.warning("⚠️ No data loaded. Click Refresh to load data.")
    
    # Only load data when explicitly requested or first load
    if refresh_clicked or (st.session_state.analysis_results is None and st.session_state.first_load):
        
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
                    # Add empty signals - just skip signal details for failed cases
                    pass
                    
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
                    # Add empty signals - skip for failed cases
                    pass
                    
                    results.append(result_row)
                    continue
                
                # Evaluate signals
                signals = evaluate_all_signals(indicators)
                
                # Count signals
                osc_buy, osc_sell, ma_buy, ma_sell = count_signals(signals)
                
                # Calculate ratings for current day
                rating1_current, rating2_current = calculate_ratings(osc_buy, osc_sell, ma_buy, ma_sell)
                
                # Calculate ratings for previous days using EXACT same logic as current day
                df_sorted = df_with_indicators.sort_values('Date')
                
                # Initialize previous day ratings
                rating1_prev1, rating2_prev1 = 'N/A', 'N/A'
                rating1_prev2, rating2_prev2 = 'N/A', 'N/A'
                
                # Calculate -1 day rating using IDENTICAL method as current day
                if len(df_sorted) >= 2:
                    try:
                        prev_date = df_sorted.iloc[-2]['Date']
                        prev_indicators = get_latest_indicators(df_with_indicators, pd.Timestamp(prev_date))
                        if prev_indicators:
                            prev_signals = evaluate_all_signals(prev_indicators)
                            prev_osc_buy, prev_osc_sell, prev_ma_buy, prev_ma_sell = count_signals(prev_signals)
                            rating1_prev1, rating2_prev1 = calculate_ratings(prev_osc_buy, prev_osc_sell, prev_ma_buy, prev_ma_sell)
                    except:
                        rating1_prev1, rating2_prev1 = 'N/A', 'N/A'
                
                # Calculate -2 day rating using IDENTICAL method as current day  
                if len(df_sorted) >= 3:
                    try:
                        prev2_date = df_sorted.iloc[-3]['Date']
                        prev2_indicators = get_latest_indicators(df_with_indicators, pd.Timestamp(prev2_date))
                        if prev2_indicators:
                            prev2_signals = evaluate_all_signals(prev2_indicators)
                            prev2_osc_buy, prev2_osc_sell, prev2_ma_buy, prev2_ma_sell = count_signals(prev2_signals)
                            rating1_prev2, rating2_prev2 = calculate_ratings(prev2_osc_buy, prev2_osc_sell, prev2_ma_buy, prev2_ma_sell)
                    except:
                        rating1_prev2, rating2_prev2 = 'N/A', 'N/A'
                
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
                    'Rating_1_Current': rating1_current,
                    'Rating_1_Prev1': rating1_prev1,
                    'Rating_1_Prev2': rating1_prev2,
                    'Rating_2_Current': rating2_current,
                    'Rating_2_Prev1': rating2_prev1,
                    'Rating_2_Prev2': rating2_prev2,
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
                # Add empty signals - skip for error cases
                pass
                
                results.append(result_row)
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        # Store results and date
        st.session_state.analysis_results = pd.DataFrame(results)
        st.session_state.last_analysis_date = selected_date
        st.session_state.first_load = False  # Mark that first load is done
    
    # Display results only if data exists
    if 'analysis_results' in st.session_state and st.session_state.analysis_results is not None:
        df_results = st.session_state.analysis_results
        
        if df_results.empty:
            st.error("No data available for the selected date.")
            st.stop()
        
        st.subheader("📊 Analysis Results")
        
        # Define only the columns to display as requested
        requested_cols = ['Sector', 'Ticker', 'Price', '% Change', 'Close_vs_MA5', 'Close_vs_MA10', 
                         'Close_vs_MA20', 'Close_vs_MA50', 'Close_vs_MA200', 'STRENGTH_ST', 
                         'STRENGTH_LT', 'Rating_1_Current', 'Rating_1_Prev1', 'Rating_1_Prev2',
                         'Rating_2_Current', 'Rating_2_Prev1', 'Rating_2_Prev2', 'MA50_GT_MA200']
        
        # Filter to only available columns
        available_columns = [col for col in requested_cols if col in df_results.columns]
        
        display_df = df_results[available_columns].copy()
        
        # Add blank column between Close_vs_MA200 and STRENGTH_ST
        blank_col_index = list(display_df.columns).index('Close_vs_MA200') + 1
        display_df.insert(blank_col_index, '　', '')  # Using full-width space as column name
        
        # Add blank column between STRENGTH_LT and Rating_1_Current
        if 'STRENGTH_LT' in display_df.columns and 'Rating_1_Current' in display_df.columns:
            blank_col_index2 = list(display_df.columns).index('STRENGTH_LT') + 1
            display_df.insert(blank_col_index2, '　　', '')  # Using double full-width space
        
        # Format numeric columns for the requested display columns
        numeric_cols = ['Close_vs_MA5', 'Close_vs_MA10', 'Close_vs_MA20', 'Close_vs_MA50', 
                       'Close_vs_MA200', 'STRENGTH_ST', 'STRENGTH_LT']
        numeric_cols = [col for col in numeric_cols if col in display_df.columns]
        
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
        
        # Configure AG-Grid with conditional formatting
        gb = GridOptionsBuilder.from_dataframe(display_df)
        
        # Configure grid options for modern style like reference image
        gb.configure_pagination(enabled=True, paginationPageSize=50)
        gb.configure_side_bar()
        gb.configure_default_column(
            groupable=False,
            value=True,
            enableRowGroup=False,
            aggFunc=None,
            editable=False,
            filter=False,  # Disable all filters
            sortable=True,
            resizable=True,
            suppressMenu=True,  # Suppress menu button
            menuTabs=[]  # Remove all menu tabs
        )
        
        # Custom CSS for AG-Grid styling - simple and direct approach
        st.markdown("""
        <style>
        /* Header cells - small font and compact */
        .ag-header-cell {
            font-size: 10px !important;
            padding: 4px 6px !important;
            font-weight: 500 !important;
        }
        
        /* Header text specifically */
        .ag-header-cell-text {
            font-size: 10px !important;
            font-weight: 500 !important;
            line-height: 1.2 !important;
        }
        
        /* Hide menu buttons completely */
        .ag-header-cell-menu-button {
            display: none !important;
        }
        
        /* Hide floating filter wrapper */
        .ag-floating-filter-wrapper {
            display: none !important;
        }
        
        /* Cell styling - keep readable size */
        .ag-cell {
            font-size: 12px !important;
            padding: 4px 6px !important;
            border-bottom: 1px solid #f3f4f6 !important;
        }
        
        /* Row height compact */
        .ag-row {
            height: 28px !important;
        }
        
        /* Header row height */
        .ag-header-row {
            height: 32px !important;
        }
        
        /* Sort indicators */
        .ag-header-cell-sortable .ag-header-cell-menu-button {
            display: none !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Configure grid theme and styling with compact layout
        gb.configure_grid_options(
            suppressRowClickSelection=True,
            rowSelection='multiple',
            enableRangeSelection=True,
            suppressMovableColumns=False,
            suppressColumnMoveAnimation=False,
            animateRows=True,
            headerHeight=24,  # Further reduced header height
            rowHeight=22,     # Further reduced row height for compact display
            suppressMenuHide=True,  # Prevent menu from showing
            suppressHeaderMenuButton=True,  # Completely suppress header menu buttons
            suppressHeaderFilterButton=True,  # Suppress header filter buttons
            defaultColDef={
                'sortable': True,
                'filter': False,  # Disable filters
                'resizable': True,
                'suppressMenu': True,  # Suppress menu for all columns
                'suppressHeaderMenuButton': True,  # Suppress menu button
                'suppressHeaderFilterButton': True,  # Suppress filter button
                'menuTabs': [],  # No menu tabs
                'autoHeaderHeight': True,  # Enable header text wrapping
                'wrapHeaderText': True,    # Wrap header text
            }
        )
        
        # Percentage renderer with normal font weight
        percentage_renderer = JsCode("""
        class PercentageRenderer {
            init(params) {
                this.eGui = document.createElement('div');
                const value = params.value;
                this.eGui.style.textAlign = 'right';
                this.eGui.style.fontSize = '12px';
                
                if (value !== null && value !== undefined && value !== 'N/A' && value !== '') {
                    // Just display the value as is (it's already formatted from Python)
                    this.eGui.innerHTML = value;
                    
                    // Try to extract numeric value for coloring
                    const stringValue = value.toString();
                    const numMatch = stringValue.match(/[-+]?[\d.]+/);
                    if (numMatch) {
                        const numValue = parseFloat(numMatch[0]);
                        if (numValue > 0) {
                            this.eGui.style.color = '#28a745';
                        } else if (numValue < 0) {
                            this.eGui.style.color = '#dc3545';
                        } else {
                            this.eGui.style.color = '#6c757d';
                        }
                    }
                } else {
                    this.eGui.innerHTML = 'N/A';
                    this.eGui.style.color = '#6c757d';
                }
            }
            
            getGui() {
                return this.eGui;
            }
        }
        """)
        
        # Color gradient renderer using alpha transparency like the reference
        color_cells = JsCode("""
        function(params) {
            if (params.value > 0) {
                let alpha = Math.min(params.value / 15, 1).toFixed(2);
                return {
                    'color': 'black',
                    'backgroundColor': `rgba(34,197,94,${alpha})`
                };
            } else if (params.value < 0) {
                let alpha = Math.min(Math.abs(params.value) / 15, 1).toFixed(2);
                return {
                    'color': 'black',
                    'backgroundColor': `rgba(239,68,68,${alpha})`
                };
            }
            return {
                'color': 'black',
                'backgroundColor': 'white'
            };
        }
        """)
        
        # Close vs MA renderer with smaller font
        close_ma_renderer = JsCode("""
        class CloseMaRenderer {
            init(params) {
                this.eGui = document.createElement('div');
                const value = params.value;
                this.eGui.style.textAlign = 'center';
                this.eGui.style.fontSize = '12px';
                
                if (value !== null && value !== undefined && value !== 'N/A') {
                    const numValue = parseFloat(value);
                    if (!isNaN(numValue)) {
                        // Display as percentage with 1 decimal place
                        this.eGui.innerHTML = numValue.toFixed(1) + '%';
                    } else {
                        this.eGui.innerHTML = 'N/A';
                    }
                } else {
                    this.eGui.innerHTML = 'N/A';
                }
            }
            
            getGui() {
                return this.eGui;
            }
        }
        """)
        
        # Strength renderer with smaller font
        strength_renderer = JsCode("""
        class StrengthRenderer {
            init(params) {
                this.eGui = document.createElement('div');
                const value = params.value;
                this.eGui.style.textAlign = 'center';
                this.eGui.style.fontSize = '12px';
                
                if (value !== null && value !== undefined && value !== 'N/A') {
                    const numValue = parseFloat(value);
                    if (!isNaN(numValue)) {
                        // Display as integer (no decimals)
                        this.eGui.innerHTML = Math.round(numValue);
                    } else {
                        this.eGui.innerHTML = value;
                    }
                } else {
                    this.eGui.innerHTML = 'N/A';
                    this.eGui.style.color = '#6c757d';
                }
            }
            
            getGui() {
                return this.eGui;
            }
        }
        """)
        
        # Simple renderer with smaller font
        simple_renderer = JsCode("""
        class SimpleRenderer {
            init(params) {
                this.eGui = document.createElement('div');
                const value = params.value;
                this.eGui.style.textAlign = 'center';
                this.eGui.style.fontSize = '12px';
                
                if (value !== null && value !== undefined && value !== 'N/A') {
                    this.eGui.innerHTML = value;
                } else {
                    this.eGui.innerHTML = 'N/A';
                    this.eGui.style.color = '#6c757d';
                }
            }
            
            getGui() {
                return this.eGui;
            }
        }
        """)
        
        # Numeric renderer with smaller font
        numeric_renderer = JsCode("""
        class NumericRenderer {
            init(params) {
                this.eGui = document.createElement('div');
                const value = params.value;
                this.eGui.style.textAlign = 'right';
                this.eGui.style.fontSize = '12px';
                
                if (value !== null && value !== undefined && value !== 'N/A') {
                    this.eGui.innerHTML = value;
                } else {
                    this.eGui.innerHTML = 'N/A';
                    this.eGui.style.color = '#6c757d';
                }
            }
            
            getGui() {
                return this.eGui;
            }
        }
        """)
        
        # MA50>MA200 renderer with smaller font
        ma_comparison_renderer = JsCode("""
        class MaComparisonRenderer {
            init(params) {
                this.eGui = document.createElement('div');
                const value = params.value;
                this.eGui.innerHTML = value || 'N/A';
                this.eGui.style.textAlign = 'center';
                this.eGui.style.fontSize = '12px';
                
                if (!value || value === 'N/A') {
                    this.eGui.style.color = '#6c757d';
                }
            }
            
            getGui() {
                return this.eGui;
            }
        }
        """)
        
        # Apply cell renderers to specific columns
        if '% Change' in display_df.columns:
            gb.configure_column('% Change', cellRenderer=percentage_renderer)
        
        # Close vs MA columns with color gradient and formatting
        close_vs_ma_cols = ['Close_vs_MA5', 'Close_vs_MA10', 'Close_vs_MA20', 'Close_vs_MA50', 'Close_vs_MA200']
        for col in close_vs_ma_cols:
            if col in display_df.columns:
                gb.configure_column(col, 
                                  cellStyle=color_cells,
                                  cellRenderer=close_ma_renderer,
                                  type=["numericColumn", "centerAligned"])
        
        # Price column with right alignment and number formatting
        if 'Price' in display_df.columns:
            gb.configure_column('Price', 
                              cellRenderer=numeric_renderer,
                              type=["numericColumn", "rightAligned"])
        
        # Strength columns without decimals, center aligned
        if 'STRENGTH_ST' in display_df.columns:
            gb.configure_column('STRENGTH_ST', cellRenderer=strength_renderer)
        if 'STRENGTH_LT' in display_df.columns:
            gb.configure_column('STRENGTH_LT', cellRenderer=strength_renderer)
        
        # Rating columns without colors (all 6 rating columns)
        rating_cols = ['Rating_1_Current', 'Rating_1_Prev1', 'Rating_1_Prev2', 
                      'Rating_2_Current', 'Rating_2_Prev1', 'Rating_2_Prev2']
        for col in rating_cols:
            if col in display_df.columns:
                gb.configure_column(col, cellRenderer=simple_renderer)
        
        # MA50>MA200 column with colors
        if 'MA50_GT_MA200' in display_df.columns:
            gb.configure_column('MA50_GT_MA200', cellRenderer=ma_comparison_renderer)
        
        # Add consistent font renderer for text columns
        text_renderer = JsCode("""
        class TextRenderer {
            init(params) {
                this.eGui = document.createElement('div');
                const value = params.value;
                this.eGui.style.textAlign = 'left';
                this.eGui.style.fontSize = '12px';
                this.eGui.innerHTML = value || 'N/A';
            }
            
            getGui() {
                return this.eGui;
            }
        }
        """)
        
        # Configure optimized column widths with consistent font
        gb.configure_column('Sector', width=60, headerName='Sector', cellRenderer=text_renderer, suppressMenu=True)
        gb.configure_column('Ticker', width=70, headerName='Ticker', cellRenderer=text_renderer, suppressMenu=True)  # Removed pinned
        gb.configure_column('Price', width=80, headerName='Price', suppressMenu=True)
        gb.configure_column('% Change', width=85, headerName='% Change', suppressMenu=True)
        
        # Close vs MA columns with shorter headers and compact width
        gb.configure_column('Close_vs_MA5', width=75, headerName='vs MA5', suppressMenu=True)
        gb.configure_column('Close_vs_MA10', width=75, headerName='vs MA10', suppressMenu=True)
        gb.configure_column('Close_vs_MA20', width=75, headerName='vs MA20', suppressMenu=True)
        gb.configure_column('Close_vs_MA50', width=75, headerName='vs MA50', suppressMenu=True)
        gb.configure_column('Close_vs_MA200', width=75, headerName='vs MA200', suppressMenu=True)
        
        # Blank columns
        gb.configure_column('　', width=20, headerName='', sortable=False, filter=False, suppressMenu=True, menuTabs=[])
        gb.configure_column('　　', width=20, headerName='', sortable=False, filter=False, suppressMenu=True, menuTabs=[])
        
        gb.configure_column('STRENGTH_ST', width=80, headerName='ST\nStrength', suppressMenu=True)
        gb.configure_column('STRENGTH_LT', width=80, headerName='LT\nStrength', suppressMenu=True)
        
        # Rating columns with date headers
        gb.configure_column('Rating_1_Current', width=70, headerName='R1\nToday', suppressMenu=True)
        gb.configure_column('Rating_1_Prev1', width=70, headerName='R1\n-1d', suppressMenu=True)
        gb.configure_column('Rating_1_Prev2', width=70, headerName='R1\n-2d', suppressMenu=True)
        gb.configure_column('Rating_2_Current', width=70, headerName='R2\nToday', suppressMenu=True)
        gb.configure_column('Rating_2_Prev1', width=70, headerName='R2\n-1d', suppressMenu=True)
        gb.configure_column('Rating_2_Prev2', width=70, headerName='R2\n-2d', suppressMenu=True)
        
        gb.configure_column('MA50_GT_MA200', width=85, headerName='MA50>\nMA200', suppressMenu=True)
        
        # Build grid options
        grid_options = gb.build()
        
        # Display AG-Grid without scrolling
        AgGrid(
            display_df,
            gridOptions=grid_options,
            data_return_mode=DataReturnMode.AS_INPUT,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            fit_columns_on_grid_load=True,
            theme='balham',  # Modern light theme
            enable_enterprise_modules=False,
            height=None,  # Auto height, no scrolling
            width='100%',
            allow_unsafe_jscode=True  # Required for custom JsCode renderers
        )
        
        # Summary statistics
        st.subheader("📈 Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_stocks = len(df_results)
            st.metric("Total Stocks", f"{total_stocks}")
        
        with col2:
            if 'Rating_1' in df_results.columns:
                buy_ratings = len(df_results[df_results['Rating_1'].isin(['Buy', 'Strong Buy'])])
                st.metric("Buy Ratings", f"{buy_ratings}")
            else:
                st.metric("Buy Ratings", "N/A")
        
        with col3:
            if 'MA50_GT_MA200' in df_results.columns:
                bullish_trend = len(df_results[df_results['MA50_GT_MA200'] == 'Yes'])
                st.metric("Bullish Trend", f"{bullish_trend}")
            else:
                st.metric("Bullish Trend", "N/A")
        
        with col4:
            if 'STRENGTH_ST' in df_results.columns:
                avg_strength_st = df_results['STRENGTH_ST'].apply(pd.to_numeric, errors='coerce').mean()
                if pd.notna(avg_strength_st):
                    st.metric("Avg ST Strength", f"{avg_strength_st:.2f}")
                else:
                    st.metric("Avg ST Strength", "N/A")
            else:
                st.metric("Avg ST Strength", "N/A")
    
    else:
        # No data loaded yet
        st.info("👆 Please click 'Refresh Data' button to load analysis results.")

except Exception as e:
    st.error(f"Error during analysis: {str(e)}")