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
- Technical Analysis Summary Table (single page design)
- Date picker with intelligent trading day default
- Comprehensive indicator display with TradingView-compatible values
- Real-time progress tracking during analysis
- Color-coded signal visualization
- All stocks/indices analysis (no filtering)

**Charts Page** (`pages/1_📈_Charts.py`):
- Reserved for future charting functionality
- Placeholder for interactive technical analysis charts

**Session State Management**:
- Caches analysis results in `st.session_state.analysis_results`
- 5-minute TTL caching on data fetching
- Auto-refresh on parameter changes

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

**Main Table Structure**:
- **Basic Info**: Sector, Ticker, Price, % Change, Osc Buy, Osc Sell, MA Buy, MA Sell
- **Signal Columns**: All oscillator and MA signals with color coding
  - 🟢 Buy signals: Green background
  - 🔴 Sell signals: Red background  
  - 🟡 Neutral signals: Yellow background
- **All Indicator Values**: Complete technical analysis with proper formatting
  - Numeric indicators: 4 decimal places
  - Price data: 2 decimal places
  - Organized by logical groups (Ichimoku, SMA, EMA, etc.)

### Export System

**Future Enhancement** (`src/utils/export_utils.py`):
- CSV: Plain text with all indicator values and signals
- Excel: Color-coded signals (Buy=Green, Sell=Red, Neutral=Yellow)
- Auto-generated filenames with timestamps

## Development Notes

### TradingView Compatibility
- Indicator values match TradingView within acceptable tolerance (data source differences)
- Scaling adjustments ensure proper display compatibility
- Signal logic follows TradingView conventions

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