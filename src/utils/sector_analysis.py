import pandas as pd
import numpy as np

# Sector mapping from English to Vietnamese
SECTOR_MAPPING = {
    'CK': 'Chứng khoán',
    'BDS': 'Bất động sản',
    'DTC': 'Xây dựng & ĐTC, VLXD',
    'XD': 'Xây dựng & ĐTC, VLXD',
    'VLXD': 'Xây dựng & ĐTC, VLXD',
    'DAU': 'Dầu, Hàng không, Agri',
    'HK': 'Dầu, Hàng không, Agri',
    'AGRI': 'Dầu, Hàng không, Agri',
    'XK': 'Xuất khẩu',
    'NH': 'Ngân hàng',
    'FAV': 'FAV'
}

# Different top/bottom counts per sector as shown in the image
SECTOR_COUNTS = {
    'Chứng khoán': {'top': 3, 'bottom': 3},
    'Bất động sản': {'top': 3, 'bottom': 3},
    'Xây dựng & ĐTC, VLXD': {'top': 3, 'bottom': 3},
    'Dầu, Hàng không, Agri': {'top': 3, 'bottom': 3},
    'Xuất khẩu': {'top': 2, 'bottom': 2},
    'Ngân hàng': {'top': 3, 'bottom': 3},
    'FAV': {'top': 3, 'bottom': 3}
}


def analyze_sectors_new(df_results):
    """
    New sector analysis with Vietnamese names and variable counts per sector

    Args:
        df_results: DataFrame with analysis results including Sector, Ticker, Rating_1_Current, Rating_1_Prev1

    Returns:
        Dictionary with sector analysis data for HTML table display
    """
    # Filter out rows without valid sector data and totals row
    df_valid = df_results[
        (df_results['Sector'].notna()) &
        (df_results['Sector'] != 'TOTAL') &
        (df_results['Sector'] != 'Index') &  # Exclude Index sector
        (df_results['Sector'] != '')
    ].copy()

    # Convert rating columns to numeric, handling 'N/A' values
    for col in ['Rating_1_Current', 'Rating_1_Prev1']:
        df_valid[col] = pd.to_numeric(df_valid[col], errors='coerce')

    # Calculate rating change (T - T-1)
    df_valid['Rating_Change'] = df_valid['Rating_1_Current'] - df_valid['Rating_1_Prev1']

    # Group XD and DTC together as "Xây dựng & DTC"
    df_valid['Sector_Mapped'] = df_valid['Sector'].map(SECTOR_MAPPING).fillna(df_valid['Sector'])

    sector_data = {}

    # Process each mapped sector
    for vn_sector, counts in SECTOR_COUNTS.items():
        # Find all stocks in this Vietnamese sector
        sector_stocks = df_valid[df_valid['Sector_Mapped'] == vn_sector].copy()

        if len(sector_stocks) == 0:
            continue

        # Get top performers by Rating1
        top_count = counts['top']
        bottom_count = counts['bottom']

        top_rating = sector_stocks.nlargest(top_count, 'Rating_1_Current')[['Ticker', 'Rating_1_Current']]
        top_rating_data = []
        for _, row in top_rating.iterrows():
            if not pd.isna(row['Rating_1_Current']):
                rating_val = int(row['Rating_1_Current'])
                color = 'green' if rating_val > 0 else 'red' if rating_val < 0 else 'black'
                top_rating_data.append({
                    'ticker': row['Ticker'],
                    'rating': rating_val,
                    'color': color
                })

        # Get bottom performers by Rating1
        bottom_rating = sector_stocks.nsmallest(bottom_count, 'Rating_1_Current')[['Ticker', 'Rating_1_Current']]
        bottom_rating_data = []
        for _, row in bottom_rating.iterrows():
            if not pd.isna(row['Rating_1_Current']):
                rating_val = int(row['Rating_1_Current'])
                color = 'green' if rating_val > 0 else 'red' if rating_val < 0 else 'black'
                bottom_rating_data.append({
                    'ticker': row['Ticker'],
                    'rating': rating_val,
                    'color': color
                })

        sector_data[vn_sector] = {
            'top_rating_data': top_rating_data,
            'bottom_rating_data': bottom_rating_data
        }

    # Calculate breakthrough groups (±10 points)
    breakthrough_up = df_valid[df_valid['Rating_Change'] >= 10].copy()
    breakthrough_down = df_valid[df_valid['Rating_Change'] <= -10].copy()


    breakthrough_up_str = ', '.join([
        f"{row['Ticker']} ({int(row['Rating_1_Prev1'])} -> {int(row['Rating_1_Current'])})"
        for _, row in breakthrough_up.iterrows()
        if not pd.isna(row['Rating_Change'])
    ])

    breakthrough_down_str = ', '.join([
        f"{row['Ticker']} ({int(row['Rating_1_Prev1'])} -> {int(row['Rating_1_Current'])})"
        for _, row in breakthrough_down.iterrows()
        if not pd.isna(row['Rating_Change'])
    ])


    return {
        'sectors': sector_data,
        'breakthrough_up': breakthrough_up_str if breakthrough_up_str else '',
        'breakthrough_down': breakthrough_down_str if breakthrough_down_str else ''
    }


def create_sector_dataframe(sector_analysis):
    """
    Create DataFrame for sector summary display using Streamlit dataframe

    Args:
        sector_analysis: Dictionary from analyze_sectors_new()

    Returns:
        DataFrame formatted for Streamlit display
    """
    if not sector_analysis or 'sectors' not in sector_analysis:
        return pd.DataFrame()

    # Define sector order as shown in the image
    sector_order = [
        'Chứng khoán', 'Bất động sản', 'Xây dựng & ĐTC, VLXD', 'Dầu, Hàng không, Agri',
        'Xuất khẩu', 'Ngân hàng', 'FAV'
    ]

    rows = []
    sectors = sector_analysis['sectors']

    # Add rows for each sector
    for sector_vn in sector_order:
        if sector_vn in sectors:
            sector_data = sectors[sector_vn]

            # Create HTML strings with colors based on rating values
            top_html_parts = []
            for item in sector_data['top_rating_data']:
                color_code = '#008000' if item['color'] == 'green' else '#ff0000' if item['color'] == 'red' else '#000000'
                top_html_parts.append(f'<span style="color: {color_code};">{item["ticker"]} ({item["rating"]})</span>')
            top_rating_html = ', '.join(top_html_parts)

            bottom_html_parts = []
            for item in sector_data['bottom_rating_data']:
                color_code = '#008000' if item['color'] == 'green' else '#ff0000' if item['color'] == 'red' else '#000000'
                bottom_html_parts.append(f'<span style="color: {color_code};">{item["ticker"]} ({item["rating"]})</span>')
            bottom_rating_html = ', '.join(bottom_html_parts)

            rows.append({
                'Rating': sector_vn,
                'Top cao điểm': top_rating_html,
                'Top thấp điểm': bottom_rating_html
            })

    # Add breakthrough groups - use special format for merging
    rows.append({
        'Rating': 'Nhóm đột phá',
        'Top cao điểm': sector_analysis['breakthrough_up'],
        'Top thấp điểm': '🔀 MERGE'  # Special marker for merge
    })

    rows.append({
        'Rating': 'Nhóm giảm điểm',
        'Top cao điểm': sector_analysis['breakthrough_down'],
        'Top thấp điểm': '🔀 MERGE'  # Special marker for merge
    })

    df = pd.DataFrame(rows)
    return df


def create_sector_html_table(sector_analysis):
    """
    Create HTML table with merged cells for breakthrough groups (deprecated - now using DataFrame approach)
    """
    return "<p>This function is deprecated. Use create_sector_dataframe() instead.</p>"


def create_sector_summary_table(sector_summary, df_results):
    """
    Create a formatted DataFrame for sector summary display

    Args:
        sector_summary: Dictionary from analyze_sectors()
        df_results: Original results DataFrame to determine sector order

    Returns:
        DataFrame formatted for AG-Grid display
    """
    if not sector_summary:
        return pd.DataFrame()

    # Get sector order from the main results table (same order as detailed table)
    df_valid = df_results[
        (df_results['Sector'].notna()) &
        (df_results['Sector'] != 'TOTAL') &
        (df_results['Sector'] != 'Index') &
        (df_results['Sector'] != '')
    ]

    # Get unique sectors in order they appear in the data
    sectors_in_order = df_valid['Sector'].unique().tolist()
    # Filter to only sectors that have summary data
    sectors = [sector for sector in sectors_in_order if sector in sector_summary]

    rows = []

    # Top 3 rating1 row
    top_rating_row = {'Sector': 'Top 3 Rating1'}
    for sector in sectors:
        top_rating_row[sector] = sector_summary[sector]['top3_rating']
    rows.append(top_rating_row)

    # Bottom 3 rating1 row (empty metric for cleaner look)
    bottom_rating_row = {'Sector': ''}
    for sector in sectors:
        bottom_rating_row[sector] = sector_summary[sector]['bottom3_rating']
    rows.append(bottom_rating_row)

    # Top 3 rating change row
    top_change_row = {'Sector': 'Top 3 Rating Change'}
    for sector in sectors:
        top_change_row[sector] = sector_summary[sector]['top3_change']
    rows.append(top_change_row)

    # Bottom 3 rating change row (empty metric for cleaner look)
    bottom_change_row = {'Sector': ''}
    for sector in sectors:
        bottom_change_row[sector] = sector_summary[sector]['bottom3_change']
    rows.append(bottom_change_row)

    df = pd.DataFrame(rows)

    # Reorder columns to have Sector first, then sectors in original data order
    column_order = ['Sector'] + sectors
    df = df[column_order]

    return df