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

def analyze_strategy():
    try:
        print("Initializing database...")
        database.init_db()
        
        ticker = "^GSPC"
        
        # 1. Check what we have in DB
        last_date = database.get_latest_date(ticker)
        
        today = pd.Timestamp.today().date()
        
        # 2. Determine download range
        if last_date:
            print(f"Found data up to {last_date}. Checking for new data...")
            start_date = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            print("No data in DB. Downloading full history...")
            start_date = "1928-01-01"
            
        end_date = pd.Timestamp.today().strftime('%Y-%m-%d')
        
        # 3. Download only if start_date < today
        # Convert start_date string back to date object for comparison
        start_date_obj = pd.to_datetime(start_date).date()
        
        if start_date_obj <= today:
            print(f"Downloading from {start_date} to {end_date}...")
            new_data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            
            if not new_data.empty:
                # Handle MultiIndex if present (yfinance quirk)
                if isinstance(new_data.columns, pd.MultiIndex):
                    # Try to handle the structure flexibly
                    try:
                        # If ticker is in level 1
                        if ticker in new_data.columns.levels[1]:
                             new_data = new_data.xs(ticker, level=1, axis=1)
                    except:
                        # If structure is different, just flatten level 0
                         new_data.columns = new_data.columns.get_level_values(0)

                print(f"Downloaded {len(new_data)} new rows.")
                database.save_stock_data(new_data, ticker)
            else:
                print("No new data found from Yahoo.")
        
        # 4. Load ALL data from DB for analysis
        print("Loading full history from database...")
        data = database.get_all_stock_data(ticker)
        
        if data.empty:
             raise Exception("No data available in database and download failed!")
             
        print(f"Total data rows: {len(data)}")

        # Calculate 200-day Simple Moving Average
        data['SMA_200'] = data['Close'].rolling(window=200).mean()

        data['Regime'] = np.where(data['Close'] > data['SMA_200'], 1, 0)
        # Shift regime by 1 day to avoid look-ahead bias (trading occurs on the next day based on today's signal)
        data['Regime'] = data['Regime'].shift(1)
        
        # Calculate daily log returns
        data['Log_Returns'] = np.log(data['Close'] / data['Close'].shift(1))
        
        # Basic Buy & Hold Strategy (1x)
        data['Strategy_1x'] = data['Log_Returns'].cumsum()
        
        # 3x Buy & Hold Strategy (New)
        # Pure leverage, always invested
        data['Strategy_3x_BH_Returns'] = 3 * data['Log_Returns']
        data['Strategy_3x_BH'] = data['Strategy_3x_BH_Returns'].cumsum()
        
        # 3x Strategy (MA Filter)
        # 3x leverage when Risk-On, 0x (Cash) when Risk-Off
        data['Strategy_3x_Returns'] = np.where(data['Regime'] == 1, 3 * data['Log_Returns'], 0)
        data['Strategy_3x'] = data['Strategy_3x_Returns'].cumsum()
        
        # Convert back to simple returns for plotting cumulative growth (exp)
        initial_capital = 10000
        data['Buy_Hold_Growth'] = initial_capital * np.exp(data['Strategy_1x'])
        data['Lev_3x_BH_Growth'] = initial_capital * np.exp(data['Strategy_3x_BH'])
        data['Lev_3x_Growth'] = initial_capital * np.exp(data['Strategy_3x'])
        
        print("Plotting results...")
        plt.figure(figsize=(12, 6))
        plt.plot(data.index, data['Buy_Hold_Growth'], label='Buy & Hold (1x)', linewidth=1)
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
        
        # Prepare Data for Table (Monthly Subset)
        # User requested to use the EXACT data points from the plot, just subsetted.
        # resample('ME') changes the Date to the end of the calendar month (e.g. 31st), even if it was specific trading day.
        # Instead, we will group by Year-Month and pick the last row of each group.
        
        # Create a YearMonth column for grouping
        data['YearMonth'] = data.index.to_period('M')
        monthly_data = data.groupby('YearMonth').tail(1)
        
        # Reset index to make Date a column for iteration
        monthly_data = monthly_data.reset_index()
        
        # Format for JSON/Template
        table_data = []
        for _, row in monthly_data.iterrows():
            table_data.append({
                'date': row['Date'].strftime('%Y-%m-%d'),
                # S&P Value usually implies the index price, but for comparison often we show the growth of $1.
                # Let's show: Date, Close (Index Value), 2x Growth ($), 3x Growth ($)
                'sp500_val': f"{row['Buy_Hold_Growth']:,.2f}",
                'strategy_3x_bh_val': f"{row['Lev_3x_BH_Growth']:,.2f}",
                'strategy_3x_val': f"{row['Lev_3x_Growth']:,.2f}"
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
