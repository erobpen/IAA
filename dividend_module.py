
import os
import io
import requests
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from datetime import datetime
from database import get_latest_market_stats_date, save_market_stats, get_all_market_stats
import data_cache
from plotting import save_plot_to_buffer

# Use Agg backend to avoid GUI issues in Docker
matplotlib.use('Agg')

SHILLER_DATA_URL = "http://www.econ.yale.edu/~shiller/data/ie_data.xls"

def download_shiller_data():
    """Downloads and parses Shiller's data, saves to DB."""
    try:
        print(f"Downloading Shiller data from {SHILLER_DATA_URL}...")
        response = requests.get(SHILLER_DATA_URL)
        response.raise_for_status()
        
        # Read Excel file
        # Skip top 7 rows which are header/notes
        df = pd.read_excel(io.BytesIO(response.content), sheet_name="Data", header=7)
        
        # Keep relevant columns
        # Shiller Excel columns (after header=7): 
        #   [0]Date [1]P [2]D [3]E [4]CPI [5]Fraction [6]Rate GS10 
        #   [7]Real Price [8]Real Dividend [9]Real TR Price [10]Real Earnings
        #   [11]Real TR Earnings [12]CAPE
        df = df.iloc[:, [0, 1, 2, 3, 4, 6, 7, 8, 10, 12]]
        df.columns = ['Date', 'SP500', 'Dividend', 'Earnings', 'CPI', 'Long Interest Rate', 'Real Price', 'Real Dividend', 'Real Earnings', 'PE10']
        
        # Drop rows where Date is NaN
        df = df.dropna(subset=['Date'])
        
        # Convert Date column (which is float like 2023.1) to datetime
        def parse_date(val):
            try:
                val_str = str(val)
                if '.' not in val_str:
                    year = int(val)
                    month = 1
                else:
                    parts = val_str.split('.')
                    year = int(parts[0])
                    month_part = round((val - year) * 100)
                    
                    if month_part == 0: month_part = 1
                    if month_part > 12: month_part = 12
                    month = int(month_part)
                    
                return datetime(year, month, 1)
            except:
                return None

        df['Date'] = df['Date'].apply(parse_date)
        df = df.dropna(subset=['Date'])
        df.set_index('Date', inplace=True)
        
        # Force numeric
        cols = ['SP500', 'Dividend', 'Earnings', 'CPI', 'Long Interest Rate', 'Real Price', 'Real Dividend', 'Real Earnings', 'PE10']
        for col in cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        save_market_stats(df)
        return True
    except Exception as e:
        print(f"Error downloading Shiller data: {e}")
        return False

def get_dividend_data():
    """Fetches and calculates dividend yield data. Uses caching."""
    cached = data_cache.get('dividend_data')
    if cached is not None:
        return cached

    # Check if we need to update data
    latest_date = get_latest_market_stats_date()
    
    # If no data, try to download
    if not latest_date:
        download_shiller_data()
        
    df = get_all_market_stats()
    
    if df.empty:
        return pd.DataFrame()
        
    # Calculate Dividend Yield: (Dividend / Price) * 100
    df['Dividend Yield'] = (df['Dividend'] / df['SP500']) * 100

    data_cache.set('dividend_data', df)
    return df

def analyze_dividend():
    """Generates plots and table data for the Dividend tab."""
    
    df = get_dividend_data()
    
    if df.empty:
        return None, []
    
    # Filter for last 100 years
    last_date = df.index.max()
    start_date = last_date - pd.DateOffset(years=100)
    df_filtered = df[df.index >= start_date].copy()
    
    # --- Generate Plot ---
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(df_filtered.index, df_filtered['Dividend Yield'], label='S&P 500 Dividend Yield (%)', color='green')
    ax.set_xlabel('Year')
    ax.set_ylabel('Yield (%)', color='green')
    ax.tick_params(axis='y', labelcolor='green')
    ax.grid(True, alpha=0.3)
    
    # Secondary y-axis for CAPE
    ax2 = ax.twinx()
    ax2.plot(df_filtered.index, df_filtered['PE10'], label='PE Ratio (CAPE)', color='#e67e22', alpha=0.7)
    ax2.set_ylabel('PE Ratio (CAPE)', color='#e67e22')
    ax2.tick_params(axis='y', labelcolor='#e67e22')
    
    ax.set_title('S&P 500 Dividend Yield & CAPE (Last 100 Years)')
    
    # Combined legend
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
    
    img = save_plot_to_buffer(fig)
    
    # --- Prepare Table Data (vectorized) ---
    df_sorted = df_filtered.sort_index(ascending=False)
    
    table_data = []
    dates = df_sorted.index.strftime('%Y-%m')
    sp500_vals = df_sorted['SP500'].values
    div_vals = df_sorted['Dividend'].values
    yield_vals = df_sorted['Dividend Yield'].values
    pe_vals = df_sorted['PE10'].values
    
    for i in range(len(df_sorted)):
        pe_str = f"{pe_vals[i]:.2f}" if pd.notna(pe_vals[i]) else "-"
        table_data.append({
            'date': dates[i],
            'sp500': f"{sp500_vals[i]:.2f}",
            'dividend': f"{div_vals[i]:.2f}",
            'yield': f"{yield_vals[i]:.2f}%",
            'pe_ratio': pe_str
        })
        
    return img, table_data
