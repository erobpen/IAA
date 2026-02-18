
import os
import io
import requests
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from datetime import datetime
from database import get_latest_market_stats_date, save_market_stats, get_all_market_stats

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
        
        # Keep relevant columns: Date, P, D, E, CPI, Fraction, Rate, Real Price, Real Dividend, Real Earnings, CAPE
        # Columns in sheet (approx index): 
        # Date(0), P(1), D(2), E(3), CPI(4), Fraction(5), Rate(6), RealPrice(7), RealDiv(8), RealEarn(9), CAPE(10)
        df = df.iloc[:, [0, 1, 2, 3, 4, 6, 7, 8, 9, 10]]
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
                    # Fraction .1 = Jan, .10 not possible usually in this format, it's .01? 
                    # Actually Shiller format: 2023.01 for Jan, 2023.1 for Oct? Need to be careful.
                    # Looking at data: 1871.01, 1871.02 ... 1871.10, 1871.11, 1871.12
                    
                    # Let's use simple logic: (val - year) * 100 rounded
                    fraction = float("0." + parts[1])
                    # Re-calculate from original float val to avoid string parse error
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
    """Fetches and calculates dividend yield data."""
    # Check if we need to update data
    latest_date = get_latest_market_stats_date()
    
    # If no data or data is old, try to download
    if not latest_date:
        download_shiller_data()
        
    df = get_all_market_stats()
    
    if df.empty:
        return pd.DataFrame()
        
    # Calculate Dividend Yield: (Dividend / Price) * 100
    df['Dividend Yield'] = (df['Dividend'] / df['SP500']) * 100
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
    plt.figure(figsize=(10, 6))
    plt.plot(df_filtered.index, df_filtered['Dividend Yield'], label='S&P 500 Dividend Yield (%)', color='green')
    
    plt.title('S&P 500 Dividend Yield (Last 100 Years)')
    plt.xlabel('Year')
    plt.ylabel('Yield (%)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Save plot to buffer
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    plt.close()
    
    # --- Prepare Table Data ---
    # Sort descending by date
    df_filtered = df_filtered.sort_index(ascending=False)
    
    table_data = []
    for date, row in df_filtered.iterrows():
        table_data.append({
            'date': date.strftime('%Y-%m'),
            'sp500': f"{row['SP500']:.2f}",
            'dividend': f"{row['Dividend']:.2f}",
            'yield': f"{row['Dividend Yield']:.2f}%",
            'pe_ratio': f"{row['PE10']:.2f}" if pd.notnull(row['PE10']) else "-"
        })
        
    return img, table_data
