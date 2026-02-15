import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg') # Set backend before importing pyplot
import matplotlib.pyplot as plt
import os
import io
import traceback
from datetime import timedelta
import database

def get_strategy_data():
    """
    Fetches data and performs all strategy calculations.
    Returns the prepared DataFrame.
    """
    print("Getting strategy data...")
    database.init_db()
    
    ticker = "^GSPC"
    
    # 1. Check what we have in DB
    last_date = database.get_latest_date(ticker)
    
    today = pd.Timestamp.today().date()
    
    # 2. Determine download range
    if last_date:
        start_date = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        start_date = "1928-01-01"
        
    end_date = pd.Timestamp.today().strftime('%Y-%m-%d')
    
    # 3. Download only if start_date < today
    start_date_obj = pd.to_datetime(start_date).date()
    
    if start_date_obj <= today:
        try:
            new_data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            
            if not new_data.empty:
                # Handle MultiIndex if present
                if isinstance(new_data.columns, pd.MultiIndex):
                    try:
                        if ticker in new_data.columns.levels[1]:
                             new_data = new_data.xs(ticker, level=1, axis=1)
                    except:
                         new_data.columns = new_data.columns.get_level_values(0)

                database.save_stock_data(new_data, ticker)
        except Exception as e:
            print(f"Error downloading data: {e}")
    
    # 4. Load ALL data from DB for analysis
    data = database.get_all_stock_data(ticker)
    
    if data.empty:
         return pd.DataFrame()

    # Calculate 200-day Simple Moving Average
    data['SMA_200'] = data['Close'].rolling(window=200).mean()

    data['Regime'] = np.where(data['Close'] > data['SMA_200'], 1, 0)
    # Shift regime by 1 day to avoid look-ahead bias
    data['Regime'] = data['Regime'].shift(1)
    
    # Calculate daily simple returns (Price Return)
    data['Simple_Ref'] = data['Close'].pct_change()
    data['Simple_Ref'].fillna(0, inplace=True)
    
    # Simulated Total Return (Adding Dividends) -> 0 as per user request
    daily_dividend = 0
    data['Total_Return_Daily'] = data['Simple_Ref'] + daily_dividend
    
    # Initial Capital
    initial_capital = 10000
    
    # 1. Buy & Hold (1x)
    data['Strategy_1x_Daily'] = data['Total_Return_Daily']
    data['Buy_Hold_Growth'] = initial_capital * (1 + data['Strategy_1x_Daily']).cumprod()
    
    # 2. 3x Buy & Hold
    data['Strategy_3x_BH_Daily'] = 3 * data['Total_Return_Daily']
    # Constraint
    data['Strategy_3x_BH_Daily'] = data['Strategy_3x_BH_Daily'].clip(lower=-1.0)
    data['Lev_3x_BH_Growth'] = initial_capital * (1 + data['Strategy_3x_BH_Daily']).cumprod()
    
    # 3. 3x Strategy (MA Filter)
    data['Strategy_3x_Daily'] = np.where(data['Regime'] == 1, 3 * data['Total_Return_Daily'], 0)
    data['Strategy_3x_Daily'] = data['Strategy_3x_Daily'].clip(lower=-1.0)
    data['Lev_3x_Growth'] = initial_capital * (1 + data['Strategy_3x_Daily']).cumprod()
    
    return data

def analyze_strategy():
    try:
        data = get_strategy_data()
        
        if data.empty:
             raise Exception("No data available!")
             
        # ... Rest of plotting code ...
        
        print("Plotting results...")
        plt.figure(figsize=(12, 6))
        plt.plot(data.index, data['Buy_Hold_Growth'], label='Buy & Hold (1x Total Return)', linewidth=1)
        plt.plot(data.index, data['Lev_3x_BH_Growth'], label='3x Buy & Hold', linewidth=1, color='orange')
        plt.plot(data.index, data['Lev_3x_Growth'], label='3x Strategy (MA)', linewidth=1, color='purple')
        
        plt.yscale('log')
        plt.title('Leverage for the Long Run: Portfolio Value ($10k Initial)')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value ($)')
        plt.legend()
        plt.grid(True, which="both", ls="-", alpha=0.2)
        
        output = io.BytesIO()
        plt.savefig(output, format='png')
        output.seek(0)
        print("Analysis complete. Returning image buffer.")
        plt.close() # Close plot to free memory
        
        # Prepare Data for Table (Full Daily Data)
        # User requested EVERY available data point (Daily).
        
        # Reset index to make Date a column for iteration
        full_data = data.reset_index()
        
        # Format for JSON/Template
        table_data = []
        for _, row in full_data.iterrows():
            # Calculate Scaled SMA (to compare with $10k scaled S&P value)
            # Scaled_SMA = Portfolio_Value * (Raw_SMA / Raw_Price)
            # Handle edge case where SMA might be NaN (start of data)
            if pd.notna(row['SMA_200']) and row['Close'] != 0:
                scaled_sma = row['Buy_Hold_Growth'] * (row['SMA_200'] / row['Close'])
                sma_str = f"{scaled_sma:,.2f}"
            else:
                sma_str = "-"

            table_data.append({
                'date': row['Date'].strftime('%Y-%m-%d'),
                'sp500_val': f"{row['Buy_Hold_Growth']:,.2f}",
                'sma_val': sma_str,
                'strategy_3x_bh_val': f"{row['Lev_3x_BH_Growth']:,.2f}",
                'strategy_3x_val': f"{row['Lev_3x_Growth']:,.2f}",
                'regime': int(row['Regime']) if pd.notna(row['Regime']) else 0
            })
            
        # Reverse list to show newest first
        table_data.reverse()
        
        return output, table_data
    except Exception as e:
        print("Error during analysis:")
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    analyze_strategy()
