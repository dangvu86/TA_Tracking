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
    page_title="Technical Tracking Summary",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 0.2rem 0;
        background: #d4fcd5;
        color: #757575;
        border-radius: 5px;
        margin-bottom: 0.2rem;
        font-size: 0.3rem;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown("""
<div class="main-header">
    <h1>Technical Tracking Summary</h1>
</div>
""", unsafe_allow_html=True)


# Date selection

selected_date = st.date_input(
    "Select Date",
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

        # === SECTOR SUMMARY TABLE ===
        try:
            from src.utils.sector_analysis import analyze_sectors, create_sector_summary_table

            # Create sector summary
            sector_summary = analyze_sectors(df_results)

            if sector_summary:
                st.markdown("### 📊 Sector Summary")

                sector_df = create_sector_summary_table(sector_summary, df_results)

                if not sector_df.empty:
                    # Configure sector summary table
                    sector_gb = GridOptionsBuilder.from_dataframe(sector_df)

                    # Basic grid configuration
                    sector_gb.configure_pagination(enabled=False)
                    sector_gb.configure_grid_options(
                        suppressRowClickSelection=True,
                        suppressColumnMoveAnimation=False,
                        headerHeight=32,
                        rowHeight=40,  # Taller rows to accommodate multi-line content
                        suppressMenuHide=True,
                        suppressHeaderMenuButton=True,
                        suppressHeaderFilterButton=True,
                        defaultColDef={
                            'sortable': False,
                            'filter': False,
                            'resizable': True,
                            'suppressMenu': True,
                            'wrapText': True,
                            'autoHeight': True,
                        }
                    )

                    # Custom cell renderer for sector summary with word wrap
                    sector_cell_renderer = JsCode("""
                    class SectorCellRenderer {
                        init(params) {
                            this.eGui = document.createElement('div');
                            const value = params.value || '';
                            this.eGui.style.fontSize = '11px';
                            this.eGui.style.padding = '4px';
                            this.eGui.style.whiteSpace = 'pre-wrap';
                            this.eGui.style.wordWrap = 'break-word';
                            this.eGui.style.lineHeight = '1.3';
                            this.eGui.innerHTML = value;

                            if (params.colDef.field === 'Sector') {
                                this.eGui.style.fontWeight = 'bold';
                                this.eGui.style.textAlign = 'left';
                            } else {
                                this.eGui.style.textAlign = 'left';
                            }
                        }

                        getGui() {
                            return this.eGui;
                        }
                    }
                    """)

                    # Configure column widths and renderers
                    sector_gb.configure_column('Sector', width=150, headerName='Sector', cellRenderer=sector_cell_renderer)

                    # Configure sector columns
                    for col in sector_df.columns:
                        if col != 'Sector':
                            sector_gb.configure_column(col, width=250, headerName=col, cellRenderer=sector_cell_renderer)

                    # Custom CSS for sector summary table
                    st.markdown("""
                    <style>
                    /* Sector summary table styling */
                    .ag-theme-balham .ag-header-cell-text {
                        font-size: 12px !important;
                        font-weight: bold !important;
                        text-align: center !important;
                    }

                    .ag-theme-balham .ag-cell {
                        font-size: 11px !important;
                        line-height: 1.3 !important;
                    }

                    /* Light background for sector table */
                    .sector-summary .ag-row {
                        background-color: #f8f9fa !important;
                    }

                    .sector-summary .ag-row:nth-child(even) {
                        background-color: #e9ecef !important;
                    }

                    .sector-summary .ag-row-hover {
                        background-color: #dee2e6 !important;
                    }
                    </style>
                    """, unsafe_allow_html=True)

                    # Display sector summary table
                    sector_grid_options = sector_gb.build()

                    AgGrid(
                        sector_df,
                        gridOptions=sector_grid_options,
                        data_return_mode=DataReturnMode.AS_INPUT,
                        update_mode=GridUpdateMode.NO_UPDATE,
                        theme='balham',
                        enable_enterprise_modules=False,
                        height=250,  # Compact height
                        width='100%',
                        allow_unsafe_jscode=True,
                        custom_css={
                            ".ag-theme-balham": {
                                "font-size": "11px"
                            }
                        },
                        key='sector_summary_grid'  # Unique key to avoid conflicts
                    )

               

        except Exception as e:
            st.warning(f"Error creating sector summary: {str(e)}")


        
        # Define only the columns to display as requested
        requested_cols = ['Sector', 'Ticker', 'Price', '% Change', 'Close_vs_MA5', 'Close_vs_MA10', 
                         'Close_vs_MA20', 'Close_vs_MA50', 'Close_vs_MA200', 'STRENGTH_ST', 
                         'STRENGTH_LT', 'Rating_1_Current', 'Rating_1_Prev1', 'Rating_1_Prev2',
                         'Rating_2_Current', 'Rating_2_Prev1', 'Rating_2_Prev2', 'MA50_GT_MA200']
        
        # Filter to only available columns
        available_columns = [col for col in requested_cols if col in df_results.columns]
        
        display_df = df_results[available_columns].copy()
        
        # Calculate totals for numeric columns
        totals_row = {}
        for col in display_df.columns:
            if col in ['STRENGTH_ST', 'STRENGTH_LT', 'Rating_1_Current', 'Rating_1_Prev1', 'Rating_1_Prev2', 
                      'Rating_2_Current', 'Rating_2_Prev1', 'Rating_2_Prev2']:
                # Sum numeric values
                numeric_values = pd.to_numeric(display_df[col], errors='coerce')
                total_sum = numeric_values.sum() if not numeric_values.isna().all() else 0
                totals_row[col] = total_sum if total_sum != 0 else ''  # Empty if zero
            elif col == 'Sector':
                totals_row[col] = 'TOTAL'
            elif col == 'Ticker':
                totals_row[col] = f'({len(display_df)} stocks)'
            else:
                totals_row[col] = ' '  # Empty for non-summed columns
        
        # Add totals row to dataframe
        totals_df = pd.DataFrame([totals_row])
        display_df = pd.concat([display_df, totals_df], ignore_index=True)
        
        # Add blank column between Close_vs_MA200 and STRENGTH_ST
        blank_col_index = list(display_df.columns).index('Close_vs_MA200') + 1
        display_df.insert(blank_col_index, '　', '')  # Using full-width space as column name
        
        # Add blank column between STRENGTH_LT and Rating_1_Current
        if 'STRENGTH_LT' in display_df.columns and 'Rating_1_Current' in display_df.columns:
            blank_col_index2 = list(display_df.columns).index('STRENGTH_LT') + 1
            display_df.insert(blank_col_index2, '　　', '')  # Using double full-width space
        
        # Add blank column between Rating_1_Prev2 and Rating_2_Current
        if 'Rating_1_Prev2' in display_df.columns and 'Rating_2_Current' in display_df.columns:
            blank_col_index3 = list(display_df.columns).index('Rating_1_Prev2') + 1
            display_df.insert(blank_col_index3, '　　　', '')  # Using triple full-width space
        
        # Format numeric columns for the requested display columns
        numeric_cols = ['Close_vs_MA5', 'Close_vs_MA10', 'Close_vs_MA20', 'Close_vs_MA50', 
                       'Close_vs_MA200', 'STRENGTH_ST', 'STRENGTH_LT']
        numeric_cols = [col for col in numeric_cols if col in display_df.columns]
        
        # Format price and % change
        def format_price(x):
            try:
                return f"{float(x):.1f}" if pd.notna(x) and isinstance(x, (int, float)) else ""
            except:
                return ""
        
        def format_change(x):
            try:
                return f"{float(x):.1f}%" if pd.notna(x) and isinstance(x, (int, float)) else ""
            except:
                return ""
        
        if 'Price' in display_df.columns:
            display_df['Price'] = display_df['Price'].apply(format_price)
        if '% Change' in display_df.columns:
            display_df['% Change'] = display_df['% Change'].apply(format_change)
        
        # Format all numeric indicator columns
        def format_numeric(x):
            try:
                if pd.isna(x):
                    return ""
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
        gb.configure_pagination(enabled=False)  # Disable pagination
        gb.configure_side_bar()
        
        # Custom CSS for AG-Grid styling - simple and direct approach
        st.markdown("""
        <style>
        /* Hide menu buttons completely */
        .ag-header-cell-menu-button {
            display: none !important;
        }
        
        /* Hide floating filter wrapper */
        .ag-floating-filter-wrapper {
            display: none !important;
        }
        
        /* Header font size and center alignment */
        .ag-header-cell-text {
            font-size: 11px !important;
            font-weight: 600 !important;
            text-align: center !important;
        }
        
        /* Center align header content */
        .ag-header-cell {
            text-align: center !important;
        }
        
        /* Force header font size with more specific selectors */
        .ag-theme-balham .ag-header-cell-text {
            font-size: 11px !important;
        }
        
        .ag-theme-balham .ag-header-cell-label {
            font-size: 11px !important;
        }
        
        /* Cell styling */
        .ag-cell {
            font-size: 12px !important;
            padding: 4px 6px !important;
            border-bottom: 1px solid #f3f4f6 !important;
        }
        
        /* Ensure background fills entire cell */
        .ag-cell > div {
            width: 100% !important;
            height: 100% !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        
        /* Row hover effect - green color */
        .ag-row-hover {
            background-color: #dcfce7 !important;
        }
        
        /* Style for totals row - make it stand out and override gradients */
        .ag-row:last-child {
            background-color: #dcfce7 !important;
            border-top: 2px solid #6c757d !important;
            font-weight: bold !important;
        }
        
        .ag-row:last-child .ag-cell {
            background-color: #dcfce7 !important;
            font-weight: bold !important;
        }
        
        /* Override gradients for totals row - force white background for all cells */
        .ag-row:last-child .ag-cell > div {
            background-color: transparent !important;
        }
        
        /* Override hover for totals row */
        .ag-row:last-child.ag-row-hover {
            background-color: #dcfce7 !important;
        }
        
        .ag-row:last-child.ag-row-hover .ag-cell {
            background-color: #dcfce7 !important;
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
            headerHeight=28,
            rowHeight=24,
            suppressMenuHide=True,
            suppressHeaderMenuButton=True,
            suppressHeaderFilterButton=True,
            alwaysShowHorizontalScroll=True,
            alwaysShowVerticalScroll=True,
            suppressHorizontalScroll=False,
            suppressAutoSize=True,  # Prevent auto-sizing that overrides width settings
            defaultColDef={
                'sortable': True,
                'filter': False,
                'resizable': True,
                'suppressMenu': True,
                'suppressHeaderMenuButton': True,
                'suppressHeaderFilterButton': True,
                'menuTabs': [],
                'autoHeaderHeight': True,
                'wrapHeaderText': True,
                'suppressAutoSize': True,  # Prevent individual columns from auto-sizing
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
                
                if (value !== null && value !== undefined && value !== '' && value !== '') {
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
                    this.eGui.innerHTML = '';
                    this.eGui.style.color = '#6c757d';
                }
            }
            
            getGui() {
                return this.eGui;
            }
        }
        """)
        
        # Calculate max/min values for gradient scaling (exclude totals row)
        close_vs_ma_cols = ['Close_vs_MA5', 'Close_vs_MA10', 'Close_vs_MA20', 'Close_vs_MA50', 'Close_vs_MA200']
        all_values = []
        for col in close_vs_ma_cols:
            if col in display_df.columns:
                # Exclude last row (totals) from gradient calculation
                numeric_values = pd.to_numeric(display_df[col].iloc[:-1], errors='coerce').dropna()
                all_values.extend(numeric_values.tolist())
        
        if all_values:
            min_val = min(all_values)  # Keep negative as is
            max_val = max(all_values)  # Keep positive as is
        else:
            min_val = -15  # fallback
            max_val = 15   # fallback
        
        # Color gradient renderer with dynamic scaling and lighter colors
        color_cells = JsCode(f"""
        function(params) {{
            const minVal = {min_val};
            const maxVal = {max_val};
            if (params.value > 0) {{
                let alpha = Math.min(params.value / maxVal, 1) * 0.5;  // Max alpha 0.5 for lighter color
                return {{
                    'color': 'black',
                    'backgroundColor': `rgba(34,197,94,${{alpha}})`
                }};
            }} else if (params.value < 0) {{
                let alpha = Math.min(params.value / minVal, 1) * 0.5;  // Use minVal directly (negative)
                return {{
                    'color': 'black',
                    'backgroundColor': `rgba(239,68,68,${{alpha}})`
                }};
            }}
            return {{
                'color': 'black',
                'backgroundColor': 'white'
            }};
        }}
        """)
        
        # Calculate max/min values for STRENGTH columns (exclude totals row)
        strength_cols = ['STRENGTH_ST', 'STRENGTH_LT']
        strength_values = []
        for col in strength_cols:
            if col in display_df.columns:
                # Exclude last row (totals) from gradient calculation
                numeric_values = pd.to_numeric(display_df[col].iloc[:-1], errors='coerce').dropna()
                strength_values.extend(numeric_values.tolist())
        
        if strength_values:
            strength_min = min(strength_values)
            strength_max = max(strength_values)
        else:
            strength_min = -50  # fallback
            strength_max = 50   # fallback
        
        # Strength gradient renderer
        strength_gradient_renderer = JsCode(f"""
        class StrengthGradientRenderer {{
            init(params) {{
                this.eGui = document.createElement('div');
                const value = params.value;
                this.eGui.style.textAlign = 'center';
                this.eGui.style.fontSize = '12px';
                
                const minVal = {strength_min};
                const maxVal = {strength_max};
                
                if (value !== null && value !== undefined && value !== '') {{
                    const numValue = parseFloat(value);
                    if (!isNaN(numValue)) {{
                        // Display as integer (no decimals)
                        this.eGui.innerHTML = Math.round(numValue);
                        
                        // Apply gradient background
                        if (numValue > 0) {{
                            let alpha = Math.min(numValue / maxVal, 1) * 0.5;
                            this.eGui.style.backgroundColor = `rgba(34,197,94,${{alpha}})`;
                        }} else if (numValue < 0) {{
                            let alpha = Math.min(numValue / minVal, 1) * 0.5;
                            this.eGui.style.backgroundColor = `rgba(239,68,68,${{alpha}})`;
                        }} else {{
                            this.eGui.style.backgroundColor = 'white';
                        }}
                    }} else {{
                        this.eGui.innerHTML = value;
                        this.eGui.style.backgroundColor = 'white';
                    }}
                }} else {{
                    this.eGui.innerHTML = '';
                    this.eGui.style.color = '#6c757d';
                    this.eGui.style.backgroundColor = 'white';
                }}
            }}
            
            getGui() {{
                return this.eGui;
            }}
        }}
        """)
        
        # Close vs MA renderer with smaller font
        close_ma_renderer = JsCode("""
        class CloseMaRenderer {
            init(params) {
                this.eGui = document.createElement('div');
                const value = params.value;
                this.eGui.style.textAlign = 'center';
                this.eGui.style.fontSize = '12px';
                
                if (value !== null && value !== undefined && value !== '') {
                    const numValue = parseFloat(value);
                    if (!isNaN(numValue)) {
                        // Display as percentage with 1 decimal place
                        this.eGui.innerHTML = numValue.toFixed(1) + '%';
                    } else {
                        this.eGui.innerHTML = '';
                    }
                } else {
                    this.eGui.innerHTML = '';
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
                
                if (value !== null && value !== undefined && value !== '') {
                    const numValue = parseFloat(value);
                    if (!isNaN(numValue)) {
                        // Display as integer (no decimals)
                        this.eGui.innerHTML = Math.round(numValue);
                    } else {
                        this.eGui.innerHTML = value;
                    }
                } else {
                    this.eGui.innerHTML = '';
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
                
                if (value !== null && value !== undefined && value !== '') {
                    this.eGui.innerHTML = value;
                } else {
                    this.eGui.innerHTML = '';
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
                
                if (value !== null && value !== undefined && value !== '') {
                    this.eGui.innerHTML = value;
                } else {
                    this.eGui.innerHTML = '';
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
                this.eGui.innerHTML = value || '';
                this.eGui.style.textAlign = 'center';
                this.eGui.style.fontSize = '12px';
                
                if (!value || value === '') {
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
        
        # Create strength gradient style function
        strength_color_cells = JsCode(f"""
        function(params) {{
            const minVal = {strength_min};
            const maxVal = {strength_max};
            const value = parseFloat(params.value);
            
            if (!isNaN(value)) {{
                if (value > 0) {{
                    let alpha = Math.min(value / maxVal, 1) * 0.5;
                    return {{
                        'color': 'black',
                        'backgroundColor': `rgba(34,197,94,${{alpha}})`
                    }};
                }} else if (value < 0) {{
                    let alpha = Math.min(value / minVal, 1) * 0.5;
                    return {{
                        'color': 'black',
                        'backgroundColor': `rgba(239,68,68,${{alpha}})`
                    }};
                }}
            }}
            return {{
                'color': 'black',
                'backgroundColor': 'white'
            }};
        }}
        """)
        
        # Calculate max/min values for Rating 1 columns (exclude totals row)
        rating1_cols = ['Rating_1_Current', 'Rating_1_Prev1', 'Rating_1_Prev2']
        rating1_values = []
        for col in rating1_cols:
            if col in display_df.columns:
                # Exclude last row (totals) from gradient calculation
                numeric_values = pd.to_numeric(display_df[col].iloc[:-1], errors='coerce').dropna()
                rating1_values.extend(numeric_values.tolist())
        
        if rating1_values:
            rating1_min = min(rating1_values)
            rating1_max = max(rating1_values)
        else:
            rating1_min = -10  # fallback
            rating1_max = 10   # fallback
        
        # Calculate max/min values for Rating 2 columns (exclude totals row)
        rating2_cols = ['Rating_2_Current', 'Rating_2_Prev1', 'Rating_2_Prev2']
        rating2_values = []
        for col in rating2_cols:
            if col in display_df.columns:
                # Exclude last row (totals) from gradient calculation
                numeric_values = pd.to_numeric(display_df[col].iloc[:-1], errors='coerce').dropna()
                rating2_values.extend(numeric_values.tolist())
        
        if rating2_values:
            rating2_min = min(rating2_values)
            rating2_max = max(rating2_values)
        else:
            rating2_min = -10  # fallback
            rating2_max = 10   # fallback
        
        # Rating 1 gradient style function
        rating1_color_cells = JsCode(f"""
        function(params) {{
            const minVal = {rating1_min};
            const maxVal = {rating1_max};
            const value = parseFloat(params.value);
            
            if (!isNaN(value)) {{
                if (value > 0) {{
                    let alpha = Math.min(value / maxVal, 1) * 0.5;
                    return {{
                        'color': 'black',
                        'backgroundColor': `rgba(34,197,94,${{alpha}})`
                    }};
                }} else if (value < 0) {{
                    let alpha = Math.min(value / minVal, 1) * 0.5;
                    return {{
                        'color': 'black',
                        'backgroundColor': `rgba(239,68,68,${{alpha}})`
                    }};
                }}
            }}
            return {{
                'color': 'black',
                'backgroundColor': 'white'
            }};
        }}
        """)
        
        # Rating 2 gradient style function
        rating2_color_cells = JsCode(f"""
        function(params) {{
            const minVal = {rating2_min};
            const maxVal = {rating2_max};
            const value = parseFloat(params.value);
            
            if (!isNaN(value)) {{
                if (value > 0) {{
                    let alpha = Math.min(value / maxVal, 1) * 0.5;
                    return {{
                        'color': 'black',
                        'backgroundColor': `rgba(34,197,94,${{alpha}})`
                    }};
                }} else if (value < 0) {{
                    let alpha = Math.min(value / minVal, 1) * 0.5;
                    return {{
                        'color': 'black',
                        'backgroundColor': `rgba(239,68,68,${{alpha}})`
                    }};
                }}
            }}
            return {{
                'color': 'black',
                'backgroundColor': 'white'
            }};
        }}
        """)
        
        # Strength columns with gradient background, center aligned
        if 'STRENGTH_ST' in display_df.columns:
            gb.configure_column('STRENGTH_ST', 
                              cellStyle=strength_color_cells,
                              cellRenderer=strength_renderer)
        if 'STRENGTH_LT' in display_df.columns:
            gb.configure_column('STRENGTH_LT', 
                              cellStyle=strength_color_cells,
                              cellRenderer=strength_renderer)
        
        # Rating 1 columns with gradient (3 columns)
        rating1_cols = ['Rating_1_Current', 'Rating_1_Prev1', 'Rating_1_Prev2']
        for col in rating1_cols:
            if col in display_df.columns:
                gb.configure_column(col, 
                                  cellStyle=rating1_color_cells,
                                  cellRenderer=simple_renderer)
        
        # Rating 2 columns with gradient (3 columns)  
        rating2_cols = ['Rating_2_Current', 'Rating_2_Prev1', 'Rating_2_Prev2']
        for col in rating2_cols:
            if col in display_df.columns:
                gb.configure_column(col, 
                                  cellStyle=rating2_color_cells,
                                  cellRenderer=simple_renderer)
        
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
                this.eGui.innerHTML = value || '';
            }
            
            getGui() {
                return this.eGui;
            }
        }
        """)
        
        # Configure optimized column widths with consistent font
        gb.configure_column('Sector', width=61, headerName='Sector', cellRenderer=text_renderer, suppressMenu=True)
        gb.configure_column('Ticker', width=60, headerName='Ticker', cellRenderer=text_renderer, suppressMenu=True, pinned='left')  # Pin to left
        gb.configure_column('Price', width=60, headerName='Price', suppressMenu=True)
        gb.configure_column('% Change', width=65, headerName='% Change', suppressMenu=True)
        
        # Close vs MA columns with shorter headers and compact width
        gb.configure_column('Close_vs_MA5', width=60, headerName='vs\nMA5', suppressMenu=True)
        gb.configure_column('Close_vs_MA10', width=60, headerName='vs\nMA10', suppressMenu=True)
        gb.configure_column('Close_vs_MA20', width=60, headerName='vs\nMA20', suppressMenu=True)
        gb.configure_column('Close_vs_MA50', width=60, headerName='vs\nMA50', suppressMenu=True)
        gb.configure_column('Close_vs_MA200', width=60, headerName='vs\nMA200', suppressMenu=True)
        
        # Blank columns
        gb.configure_column('　', width=10, headerName='', sortable=False, filter=False, suppressMenu=True, menuTabs=[])
        gb.configure_column('　　', width=10, headerName='', sortable=False, filter=False, suppressMenu=True, menuTabs=[])
        gb.configure_column('　　　', width=10, headerName='', sortable=False, filter=False, suppressMenu=True, menuTabs=[])
        
        gb.configure_column('STRENGTH_ST', width=65, headerName='ST\nStrength', suppressMenu=True)
        gb.configure_column('STRENGTH_LT', width=65, headerName='LT\nStrength', suppressMenu=True)
        
        # Rating columns with new headers
        gb.configure_column('Rating_1_Current', width=60, headerName='Rating1\nT', suppressMenu=True)
        gb.configure_column('Rating_1_Prev1', width=60, headerName='Rating1\nT-1', suppressMenu=True)
        gb.configure_column('Rating_1_Prev2', width=60, headerName='Rating1\nT-2', suppressMenu=True)
        gb.configure_column('Rating_2_Current', width=60, headerName='Rating2\nT', suppressMenu=True)
        gb.configure_column('Rating_2_Prev1', width=60, headerName='Rating2\nT-1', suppressMenu=True)
        gb.configure_column('Rating_2_Prev2', width=60, headerName='Rating2\nT-2', suppressMenu=True)
        
        gb.configure_column('MA50_GT_MA200', width=85, headerName='MA50>\nMA200', suppressMenu=True)
        
        # Build grid options
        grid_options = gb.build()
        
        # Display AG-Grid with scrolling enabled
        AgGrid(
            display_df,
            gridOptions=grid_options,
            data_return_mode=DataReturnMode.AS_INPUT,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            fit_columns_on_grid_load=True,  # Enable to respect column width settings
            theme='balham',  # Modern light theme
            enable_enterprise_modules=False,
            height=900,  # Fixed height to enable scrolling
            width='100%',
            allow_unsafe_jscode=True  # Required for custom JsCode renderers
        )
        
       
    else:
        # No data loaded yet
        st.info("👆 Please click 'Refresh Data' button to load analysis results.")

except Exception as e:
    st.error(f"Error during analysis: {str(e)}")
