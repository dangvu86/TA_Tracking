# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Start Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run main.py

# Test vnstock integration
python -c "from src.vnstock_fetcher import test_vnstock_connection; print(test_vnstock_connection())"
```

## Architecture Overview

This is a **Streamlit 2-page web application** for technical analysis of Vietnamese and US financial markets. The architecture follows a **simplified structure** with comprehensive indicator calculation and signal evaluation optimized for TradingView compatibility.

### Core Data Flow Architecture

1. **Data Source Router** (`src/data_fetcher.py`): 
   - Routes Vietnamese symbols (stocks + VNINDEX/VNMIDCAP) → vnstock API
   - Routes US symbols/indices → Yahoo Finance API
   - Implements intelligent fallback between sources

2. **Dual API Integration**:
   - **vnstock** (`src/vnstock_fetcher.py`): Vietnamese market data
     - TCBS source for stocks and VNINDEX
     - VCI source specifically for VNMIDCAP
   - **Yahoo Finance**: US indices and fallback for Vietnamese stocks

3. **Processing Pipeline**:
   - Stock selection → Data fetching → Indicator calculation → Signal evaluation → Export

### Technical Indicators System

**Calculation Engine** (`src/indicators/calculator.py`):
- Calculates 40+ technical indicators using the `ta` library with **TradingView compatibility**
- **Key TradingView Adjustments**:
  - StochRSI: Scale 0-100 (multiply by 100)
  - Momentum: Absolute difference (Close - Close[N])  
  - MACD: Scale x1000 for display compatibility
  - Bull/Bear Power: Scale x1000
  - Awesome Oscillator: Keep original scale (no multiplication)
- Includes Ichimoku Cloud (9,26,52,26), MA/EMA series, RSI, MACD, Stochastic, etc.
- Implements custom Hull MA calculation
- Handles previous-day comparisons for oscillators
- Date sorting ensures proper chronological calculations

**Signal Evaluation** (`src/indicators/signals.py`):
- Converts raw indicator values into Buy/Sell/Neutral signals
- Implements complex rules (e.g., Ichimoku multi-condition logic)
- **Signal Counting** (`src/utils/signal_counter.py`):
  - Oscillator signals: RSI, Stochastic, CCI, ADX, AO, Momentum, MACD, StochRSI, Williams %R, BBP, UO
  - Moving Average signals: All SMA/EMA, Ichimoku, VWMA, Hull MA
  - Provides buy/sell counts by category

### Vietnamese Market Specifics

**Key Mapping**: `VNMID` → `VNMIDCAP` (handled in `format_ticker_for_vnstock()`)

**Exchange Handling**:
- HOSE/HNX/UPCOM stocks use vnstock with `.VN` suffix fallback
- Vietnamese indices (VNINDEX, VNMIDCAP) use vnstock exclusively
- Exchange validation ensures proper data source selection

### Streamlit App Structure

**Main Page** (`main.py`): 
- **AG-Grid Modern Table** with Balham light theme
- **Smart Refresh System**: Manual data loading with status indicators
- **Historical Rating System**: Shows 3-day rating history (Current, -1d, -2d)
- Date picker with intelligent trading day default
- **Compact Display**: Optimized columns for essential metrics only
- Real-time progress tracking during analysis
- **Conditional Formatting**: Color gradients for Close vs MA percentages

**Charts Page** (`pages/1_📈_Charts.py`):
- Reserved for future charting functionality
- Placeholder for interactive technical analysis charts

**Session State Management**:
- Caches analysis results in `st.session_state.analysis_results`
- **Smart Refresh Logic**: Only loads data when explicitly requested
- **First Load Flag**: Prevents unnecessary data reloading on UI changes
- Date change detection with user warnings

### Stock List Configuration

**CSV Format** (`TA_Tracking_List.csv`):
```csv
Sector,Ticker,Exchange
CK,SSI,HOSE
Index,VNINDEX,
Index,VNMID,
Index,^GSPC,
Index,^VIX,
```

**Special Handling**:
- `VNMID` → `VNMIDCAP` mapping in vnstock
- US indices use `^` prefix (^GSPC for S&P 500, ^VIX for VIX)
- Vietnamese indices (VNINDEX, VNMID) use vnstock exclusively
- All entries must have proper Sector designation to avoid NaN sorting errors

### Display & Visualization

**AG-Grid Modern Table Structure**:
- **Core Columns**: Sector, Ticker, Price, % Change
- **Close vs MA Series**: vs MA5, MA10, MA20, MA50, MA200 (with color gradient)
- **Strength Indicators**: ST Strength, LT Strength (integer display)
- **Historical Ratings**: 
  - Rating 1: Current, -1d, -2d
  - Rating 2: Current, -1d, -2d
- **Trend Indicator**: MA50>MA200 (Yes/No with color coding)

**Visual Features**:
- **Color Gradient**: Alpha transparency for Close vs MA columns
  - Green gradient for positive values
  - Red gradient for negative values  
  - Intensity based on magnitude (0-15% range)
- **Compact Design**: 12px font, optimized column widths
- **No Filters**: Clean header design without filter icons
- **Blank Separators**: Visual column grouping with spacer columns

### Export System

**Future Enhancement** (`src/utils/export_utils.py`):
- CSV: Plain text with all indicator values and signals
- Excel: Color-coded signals (Buy=Green, Sell=Red, Neutral=Yellow)
- Auto-generated filenames with timestamps

### Historical Rating System

**3-Day Rating Implementation**:
- **Current Day**: Calculated from latest indicators using standard pipeline
- **-1 Day**: Uses `get_latest_indicators()` with previous day's timestamp
- **-2 Day**: Uses `get_latest_indicators()` with -2 day's timestamp
- **Consistency**: Rating -1d (when viewing day N) = Rating Current (when viewing day N-1)

**Rating Logic**:
```python
# All days use identical calculation pipeline:
indicators = get_latest_indicators(df_with_indicators, target_date)
signals = evaluate_all_signals(indicators)
osc_buy, osc_sell, ma_buy, ma_sell = count_signals(signals)
rating1, rating2 = calculate_ratings(osc_buy, osc_sell, ma_buy, ma_sell)
```

**Performance Optimization**:
- No additional API calls for historical ratings
- Reuses existing dataframe historical data
- Efficient date-based indicator extraction

## Development Notes

### TradingView Compatibility
- Indicator values match TradingView within acceptable tolerance (data source differences)
- Scaling adjustments ensure proper display compatibility
- Signal logic follows TradingView conventions

### AG-Grid Implementation
- **Theme**: Balham light theme for modern appearance
- **Custom Renderers**: JavaScript-based cell formatting
  - Color gradient renderer with alpha transparency
  - Percentage formatter with 1 decimal place
  - Integer formatter for strength columns
  - Right/center text alignment optimizations
- **Performance**: Auto-height, no scrolling, optimized column widths
- **User Experience**: No filter dropdowns, clean header design

### Data Source Priorities
1. vnstock for Vietnamese symbols (VNINDEX, VNMID, all VN stocks)
2. Yahoo Finance for US indices (^GSPC, ^VIX)
3. Intelligent fallback handling with user warnings
4. `get_last_trading_date()` for smart date defaults

### Caching Strategy
- 5-minute TTL on all data fetching functions
- Session state caching for analysis results
- Date sorting before calculations ensures consistency

### Vietnamese Market Integration
- **VNMID mapping**: Automatically converts VNMID → VNMIDCAP for vnstock
- **VCI source**: VNMIDCAP requires VCI source specifically
- **TCBS source**: VNINDEX and stocks use TCBS source
- **Error prevention**: All CSV entries must have proper Sector values

### Error Handling Patterns
- Duplicate column prevention in dataframe construction
- Safe numeric formatting with try-catch blocks
- Graceful degradation for missing indicator data
- Progress tracking with individual stock error handling