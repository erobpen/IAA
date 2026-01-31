import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg') # Set backend before importing pyplot
import matplotlib.pyplot as plt
import os
import io
import traceback

def analyze_strategy():
    try:
        print("Downloading data...")
        # Download S&P 500 data
        ticker = "^GSPC"
        start_date = "1928-01-01"
        end_date = pd.Timestamp.today().strftime('%Y-%m-%d')
        
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        
        if data.empty:
            raise Exception("No data downloaded!")
            
        print(f"Data columns: {data.columns}")
        print(f"Data head: {data.head()}")
        
        # Determine Regime: 1 if Close > SMA_200 (Risk-On), else 0 (Risk-Off)
        # Handling potential MultiIndex in yfinance (Common issue)
        if isinstance(data.columns, pd.MultiIndex):
             data = data.xs(ticker, level=1, axis=1) if ticker in data.columns.levels[1] else data
             # Fallback if xs fails or structure is different, try to just squash if 1 ticker
             if isinstance(data.columns, pd.MultiIndex):
                 data.columns = data.columns.get_level_values(0)

        # Calculate 200-day Simple Moving Average
        data['SMA_200'] = data['Close'].rolling(window=200).mean()

        data['Regime'] = np.where(data['Close'] > data['SMA_200'], 1, 0)
        # Shift regime by 1 day to avoid look-ahead bias (trading occurs on the next day based on today's signal)
        data['Regime'] = data['Regime'].shift(1)
        
        # Calculate daily log returns
        data['Log_Returns'] = np.log(data['Close'] / data['Close'].shift(1))
        
        # Basic Buy & Hold Strategy (1x)
        data['Strategy_1x'] = data['Log_Returns'].cumsum()
        
        # "Leverage for the Long Run" Logic
        # We assume risk-free rate is 0 for simplicity in this cash position
        # 2x Strategy: 2x leverage when Risk-On, 0x (Cash) when Risk-Off
        data['Strategy_2x_Returns'] = np.where(data['Regime'] == 1, 2 * data['Log_Returns'], 0)
        data['Strategy_2x'] = data['Strategy_2x_Returns'].cumsum()
        
        # 3x Strategy: 3x leverage when Risk-On, 0x (Cash) when Risk-Off
        data['Strategy_3x_Returns'] = np.where(data['Regime'] == 1, 3 * data['Log_Returns'], 0)
        data['Strategy_3x'] = data['Strategy_3x_Returns'].cumsum()
        
        # Convert back to simple returns for plotting cumulative growth (exp)
        data['Buy_Hold_Growth'] = np.exp(data['Strategy_1x'])
        data['Lev_2x_Growth'] = np.exp(data['Strategy_2x'])
        data['Lev_3x_Growth'] = np.exp(data['Strategy_3x'])
        
        print("Plotting results...")
        plt.figure(figsize=(12, 6))
        plt.plot(data.index, data['Buy_Hold_Growth'], label='Buy & Hold (1x)', linewidth=1)
        plt.plot(data.index, data['Lev_2x_Growth'], label='Strategy 2x', linewidth=1)
        plt.plot(data.index, data['Lev_3x_Growth'], label='Strategy 3x', linewidth=1)
        
        plt.yscale('log')
        plt.title('Leverage for the Long Run: Cumulative Returns (Log Scale)')
        plt.xlabel('Date')
        plt.ylabel('Cumulative Return ($1 Invested)')
        plt.legend()
        plt.grid(True, which="both", ls="-", alpha=0.2)
        
        output = io.BytesIO()
        plt.savefig(output, format='png')
        output.seek(0)
        print("Analysis complete. Returning image buffer.")
        plt.close() # Close plot to free memory
        return output
    except Exception as e:
        print("Error during analysis:")
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    analyze_strategy()
