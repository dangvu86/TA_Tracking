import pandas as pd
import numpy as np


def analyze_sectors(df_results):
    """
    Analyze sector performance and create summary table

    Args:
        df_results: DataFrame with analysis results including Sector, Ticker, Rating_1_Current, Rating_1_Prev1

    Returns:
        Dictionary with sector analysis data for display
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

    # Get unique sectors
    sectors = sorted(df_valid['Sector'].unique())

    sector_summary = {}

    for sector in sectors:
        sector_data = df_valid[df_valid['Sector'] == sector].copy()

        if len(sector_data) == 0:
            continue

        # Top 3 by Rating1 (highest)
        top3_rating = sector_data.nlargest(3, 'Rating_1_Current')[['Ticker', 'Rating_1_Current']]
        top3_rating_str = ', '.join([
            f"{row['Ticker']} ({int(row['Rating_1_Current'])})"
            if not pd.isna(row['Rating_1_Current'])
            else f"{row['Ticker']} (N/A)"
            for _, row in top3_rating.iterrows()
        ])

        # Bottom 3 by Rating1 (lowest)
        bottom3_rating = sector_data.nsmallest(3, 'Rating_1_Current')[['Ticker', 'Rating_1_Current']]
        bottom3_rating_str = ', '.join([
            f"{row['Ticker']} ({int(row['Rating_1_Current'])})"
            if not pd.isna(row['Rating_1_Current'])
            else f"{row['Ticker']} (N/A)"
            for _, row in bottom3_rating.iterrows()
        ])

        # Top 3 by Rating Change (highest increase)
        top3_change = sector_data.nlargest(3, 'Rating_Change')[['Ticker', 'Rating_Change']]
        top3_change_str = ', '.join([
            f"{row['Ticker']} ({int(row['Rating_Change']):+d})"
            if not pd.isna(row['Rating_Change'])
            else f"{row['Ticker']} (N/A)"
            for _, row in top3_change.iterrows()
        ])

        # Bottom 3 by Rating Change (largest decrease)
        bottom3_change = sector_data.nsmallest(3, 'Rating_Change')[['Ticker', 'Rating_Change']]
        bottom3_change_str = ', '.join([
            f"{row['Ticker']} ({int(row['Rating_Change']):+d})"
            if not pd.isna(row['Rating_Change'])
            else f"{row['Ticker']} (N/A)"
            for _, row in bottom3_change.iterrows()
        ])

        sector_summary[sector] = {
            'top3_rating': top3_rating_str,
            'bottom3_rating': bottom3_rating_str,
            'top3_change': top3_change_str,
            'bottom3_change': bottom3_change_str
        }

    return sector_summary


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