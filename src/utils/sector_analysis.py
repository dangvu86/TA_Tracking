import pandas as pd
import numpy as np

# Sector mapping from English to Vietnamese
SECTOR_MAPPING = {
    'CK': 'Chứng khoán',
    'BDS': 'Bất động sản',
    'DTC': 'Xây dựng & DTC',
    'XD': 'Xây dựng & DTC',  # XD also maps to the same Vietnamese name
    'VLXD': 'VLXD',
    'DAU': 'Dầu',
    'HK': 'Hàng không',
    'AGRI': 'Agri',
    'XK': 'Xuất khẩu',
    'NH': 'Ngân hàng',
    'FAV': 'FAV'
}

# Different top/bottom counts per sector as shown in the image
SECTOR_COUNTS = {
    'Chứng khoán': {'top': 3, 'bottom': 3},
    'Bất động sản': {'top': 3, 'bottom': 3},
    'Xây dựng & DTC': {'top': 2, 'bottom': 1},
    'VLXD': {'top': 2, 'bottom': 2},
    'Dầu': {'top': 1, 'bottom': 1},
    'Hàng không': {'top': 2, 'bottom': 1},
    'Agri': {'top': 1, 'bottom': 1},
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
        top_rating_str = ', '.join([
            f"{row['Ticker']} ({int(row['Rating_1_Current'])})"
            for _, row in top_rating.iterrows()
            if not pd.isna(row['Rating_1_Current'])
        ])

        # Get bottom performers by Rating1
        bottom_rating = sector_stocks.nsmallest(bottom_count, 'Rating_1_Current')[['Ticker', 'Rating_1_Current']]
        bottom_rating_str = ', '.join([
            f"{row['Ticker']} ({int(row['Rating_1_Current'])})"
            for _, row in bottom_rating.iterrows()
            if not pd.isna(row['Rating_1_Current'])
        ])

        sector_data[vn_sector] = {
            'top_rating': top_rating_str,
            'bottom_rating': bottom_rating_str
        }

    # Calculate breakthrough groups (±10 points)
    breakthrough_up = df_valid[df_valid['Rating_Change'] >= 10].copy()
    breakthrough_down = df_valid[df_valid['Rating_Change'] <= -10].copy()

    # Debug: Print breakthrough data (can be removed in production)
    # print(f"DEBUG: Total stocks with Rating_Change data: {len(df_valid[df_valid['Rating_Change'].notna()])}")
    # print(f"DEBUG: Rating_Change range: {df_valid['Rating_Change'].min():.1f} to {df_valid['Rating_Change'].max():.1f}")
    # print(f"DEBUG: Breakthrough up (>=10): {len(breakthrough_up)} stocks")
    # print(f"DEBUG: Breakthrough down (<=-10): {len(breakthrough_down)} stocks")

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

    # If no breakthrough, try lower threshold for testing
    if not breakthrough_up_str and not breakthrough_down_str:
        print("DEBUG: No ±10 breakthrough, checking ±5...")
        breakthrough_up_5 = df_valid[df_valid['Rating_Change'] >= 5].copy()
        breakthrough_down_5 = df_valid[df_valid['Rating_Change'] <= -5].copy()
        print(f"DEBUG: ±5 threshold - Up: {len(breakthrough_up_5)}, Down: {len(breakthrough_down_5)}")

        # Show top changes for reference
        top_changes = df_valid.nlargest(3, 'Rating_Change')[['Ticker', 'Rating_Change']]
        bottom_changes = df_valid.nsmallest(3, 'Rating_Change')[['Ticker', 'Rating_Change']]
        print(f"DEBUG: Top 3 increases: {top_changes.to_dict('records')}")
        print(f"DEBUG: Top 3 decreases: {bottom_changes.to_dict('records')}")

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
        'Chứng khoán', 'Bất động sản', 'Xây dựng & DTC', 'VLXD', 'Dầu',
        'Hàng không', 'Agri', 'Xuất khẩu', 'Ngân hàng', 'FAV'
    ]

    rows = []
    sectors = sector_analysis['sectors']

    # Add rows for each sector
    for sector_vn in sector_order:
        if sector_vn in sectors:
            sector_data = sectors[sector_vn]
            rows.append({
                'Rating': sector_vn,
                'Top cao điểm': sector_data['top_rating'],
                'Top thấp điểm': sector_data['bottom_rating']
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
    Create HTML table with merged cells for breakthrough groups

    Args:
        sector_analysis: Dictionary from analyze_sectors_new()

    Returns:
        HTML string for the table
    """
    if not sector_analysis or 'sectors' not in sector_analysis:
        return "<p>Không có dữ liệu sector</p>"

    # Define sector order as shown in the image
    sector_order = [
        'Chứng khoán', 'Bất động sản', 'Xây dựng & DTC', 'VLXD', 'Dầu',
        'Hàng không', 'Agri', 'Xuất khẩu', 'Ngân hàng', 'FAV'
    ]

    html = f"""
    <div style="margin: 10px 0;">
        <table style="width: 100%; border-collapse: collapse; font-size: 12px;">
            <thead>
                <tr style="background-color: #f5f5f5;">
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: center; font-weight: bold; font-size: 10px; width: 15%;">Sector</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: center; font-weight: bold; font-size: 10px; width: 42.5%;">Top cao điểm</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: center; font-weight: bold; font-size: 10px; width: 42.5%;">Top thấp điểm</th>
                </tr>
            </thead>
            <tbody>
    """

    # Add rows for each sector
    sectors = sector_analysis['sectors']
    for sector_vn in sector_order:
        if sector_vn in sectors:
            sector_data = sectors[sector_vn]
            html += f"""
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: center; vertical-align: middle;">{sector_vn}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: center; vertical-align: middle; background-color: #e8f5e8;">{sector_data['top_rating']}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: center; vertical-align: middle; background-color: #ffe8e8;">{sector_data['bottom_rating']}</td>
                </tr>
            """

    # Add breakthrough groups with merged cells
    html += f"""
                <tr style="background-color: #f9f9f9; font-style: italic;">
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: center; vertical-align: middle;">Nhóm đột phá</td>
                    <td colspan="2" style="border: 1px solid #ddd; padding: 8px; text-align: center; vertical-align: middle;">{sector_analysis['breakthrough_up']}</td>
                </tr>
                <tr style="background-color: #f9f9f9; font-style: italic;">
                    <td style="border: 1px solid #ddd; padding: 8px; text-align: center; vertical-align: middle;">Nhóm giảm điểm</td>
                    <td colspan="2" style="border: 1px solid #ddd; padding: 8px; text-align: center; vertical-align: middle;">{sector_analysis['breakthrough_down']}</td>
                </tr>
            </tbody>
        </table>
    </div>
    """

    return html


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