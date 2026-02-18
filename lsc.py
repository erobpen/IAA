
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import traceback
import analyzer
import small_cap

def analyze_lsc():
    try:
        # 1. Get Daily Strategy Data (includes Regime and Date index)
        daily_data = analyzer.get_strategy_data()
        
        if daily_data.empty:
            return None, []

        # 2. Get Monthly Small Cap Data
        sc_data = small_cap.get_small_cap_data()
        
        if sc_data.empty:
            print("Warning: No Small Cap data found.")
            return None, []

        # 3. Preparation for Merge
        # We need to map each day in daily_data to a monthly return from sc_data.
        
        # Create a linkage column 'YearMonth'
        daily_data['YearMonth'] = daily_data.index.to_period('M')
        sc_data['YearMonth'] = sc_data.index.to_period('M')
        
        # Join
        # We want to bring 'Small_Value_Ret' (Monthly) into daily_data
        # Reset index to merge
        df_daily = daily_data.reset_index()
        
        # Ensure 'Date' column exists (if index was unnamed)
        if 'Date' not in df_daily.columns:
            # Assume the first column is the date if not named 'Date'
            # Or check if 'index' is there
            if 'index' in df_daily.columns:
                df_daily.rename(columns={'index': 'Date'}, inplace=True)
            else:
                 # Fallback: rename the first column
                 df_daily.rename(columns={df_daily.columns[0]: 'Date'}, inplace=True)

        df_sc = sc_data.reset_index()[['YearMonth', 'Small_Value_Ret']]
        df_sc = sc_data.reset_index()[['YearMonth', 'Small_Value_Ret']]
        
        merged = pd.merge(df_daily, df_sc, on='YearMonth', how='left')
        merged.set_index('Date', inplace=True)
        
        # 4. Calculate Daily Equivalent Return for Small Cap
        # Problem: 'Small_Value_Ret' is the monthly return.
        # We apply this to every day? No.
        # We need to distribute it.
        # A simple approximation: r_daily = (1 + r_monthly)^(1/trading_days) - 1
        # Count trading days per month
        
        # Group by YearMonth to count days
        trading_days_per_month = merged.groupby('YearMonth')['Close'].count()
        trading_days_per_month.name = 'TradingDays'
        
        merged = pd.merge(merged.reset_index(), trading_days_per_month, on='YearMonth', how='left')
        merged.set_index('Date', inplace=True)
        
        # Calculate SC_Daily_Return
        # Handle NaNs (e.g. current partial month in daily data might not be in SC data yet, or vice versa)
        merged['Small_Value_Ret'].fillna(0, inplace=True)
        merged['TradingDays'].fillna(21, inplace=True) # Default to 21 if unknown

        # Avoid division by zero
        merged['TradingDays'] = merged['TradingDays'].replace(0, 1)

        merged['SC_Daily_Ret'] = (1 + merged['Small_Value_Ret']) ** (1 / merged['TradingDays']) - 1
        
        # 5. Calculate LSC Strategy
        # If Regime == 1 (Bull/Risk On) -> 3x Daily (lev 3 sp500)
        # If Regime == 0 (Bear/Risk Off) -> Small Cap Daily
        
        # 'Strategy_3x_Daily' from analyzer is: np.where(Regime==1, 3*Total_Return, 0)
        # It puts 0 in Regime 0.
        # We want:
        # Regime 1: 3 * Total_Return (clipped) -> This is already in 'Strategy_3x_Daily' for Regime 1 ?? 
        # Wait, analyzer.py:
        # data['Strategy_3x_Daily'] = np.where(data['Regime'] == 1, 3 * data['Total_Return_Daily'], 0)
        
        # So we can construct LSC Daily Return:
        # If Regime == 1: 3 * Total_Return_Daily
        # If Regime == 0: SC_Daily_Ret
        
        # Recalculate to be sure logic matches
        # Note: 'Total_Return_Daily' is in merged (from analyzer)
        
        # Constraint for 3x leg
        lev_ret = (merged['Total_Return_Daily'] * 3).clip(lower=-1.0)
        
        merged['LSC_Daily_Ret'] = np.where(merged['Regime'] == 1, lev_ret, merged['SC_Daily_Ret'])
        
        # 6. Calculate Cumulative Growth
        initial_capital = 10000
        merged['LSC_Growth'] = initial_capital * (1 + merged['LSC_Daily_Ret']).cumprod()
        
        # We also need the "3x Strategy (Cash)" for comparison.
        # That is 'Lev_3x_Growth' from analyzer.
        
        # 7. Plotting
        print("Plotting LSC results...")
        plt.figure(figsize=(12, 6))
        
        # Plot Benchmark (3x Strategy with Cash)
        plt.plot(merged.index, merged['Lev_3x_Growth'], label='3x Strategy (Cash)', linewidth=1, color='purple', alpha=0.7)
        
        # Plot LSC
        plt.plot(merged.index, merged['LSC_Growth'], label='3x Strategy (Small Cap)', linewidth=1.5, color='#d946ef') # Magenta for SC vibe
        
        plt.yscale('log')
        plt.title('Leverage Strategy: Cash vs Small Cap (Risk Off)')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value ($)')
        plt.legend()
        plt.grid(True, which="both", ls="-", alpha=0.2)
        
        output = io.BytesIO()
        plt.savefig(output, format='png')
        output.seek(0)
        plt.close()
        
        # 8. Table Data
        # Columns: Date, Regime, 3x(Cash), 3x(SC), SC_Daily_Yield(Approx)
        table_records = merged.sort_index(ascending=False)
        table_data = []
        
        for date, row in table_records.iterrows():
            regime = int(row['Regime']) if pd.notna(row['Regime']) else 0
            
            table_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'regime': regime,
                'val_cash': f"{row['Lev_3x_Growth']:,.2f}",
                'val_sc': f"{row['LSC_Growth']:,.2f}",
                'sc_daily_yield': f"{row['SC_Daily_Ret']*100:.4f}%"
            })
            
        return output, table_data

    except Exception as e:
        print(f"Error in analyze_lsc: {e}")
        traceback.print_exc()
        return None, []

if __name__ == "__main__":
    analyze_lsc()
