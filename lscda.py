
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import traceback
import analyzer
import small_cap
import dividend_module

def analyze_lscda():
    try:
        # 1. Get Daily Strategy Data (includes Regime and Date index)
        # Columns: Close, SMA_200, Regime, Simple_Ref, Total_Return_Daily, Strategy_1x_Daily, Strategy_3x_BH_Daily, Strategy_3x_Daily
        daily_data = analyzer.get_strategy_data()
        
        if daily_data.empty:
            return None, []

        # 2. Get Monthly Small Cap Data
        # Columns: Small_Value_Ret
        sc_data = small_cap.get_small_cap_data()

        # 3. Get Dividend Data
        # Columns: Dividend Yield (Annual %)
        div_data = dividend_module.get_dividend_data()

        if sc_data.empty or div_data.empty:
            print("Warning: Missing SC or Dividend data.")
            return None, []

        # 4. Merge Data
        # Add YearMonth to all
        daily_data['YearMonth'] = daily_data.index.to_period('M')
        sc_data['YearMonth'] = sc_data.index.to_period('M')
        div_data['YearMonth'] = div_data.index.to_period('M')

        # Reset index for merging
        df_daily = daily_data.reset_index()
        # Ensure we have a Date column
        if 'Date' not in df_daily.columns:
             # Just in case index name was lost
             df_daily.rename(columns={df_daily.columns[0]: 'Date'}, inplace=True)

        df_sc = sc_data.reset_index()[['YearMonth', 'Small_Value_Ret']]
        df_div = div_data.reset_index()[['YearMonth', 'Dividend Yield']]

        # Merge Daily + SC
        merged = pd.merge(df_daily, df_sc, on='YearMonth', how='left')
        
        # Merge + Div
        # Note: 'Dividend Yield' is annual %.
        merged = pd.merge(merged, df_div, on='YearMonth', how='left')
        
        merged.set_index('Date', inplace=True)
        
        # 5. Calculate Daily SC Return (Same as LSC)
        # Trading days per month
        trading_days = merged.groupby('YearMonth')['Close'].transform('count')
        merged['TradingDays'] = trading_days.fillna(21).replace(0, 1) # Avoid div by zero
        
        merged['Small_Value_Ret'].fillna(0, inplace=True)
        merged['SC_Daily_Ret'] = (1 + merged['Small_Value_Ret']) ** (1 / merged['TradingDays']) - 1
        
        # 6. Calculate Daily Dividend Yield
        # Annual Yield % -> Daily Yield decimal
        # div_yield_daily = (1 + annual_yield/100)^(1/252) - 1
        merged['Dividend Yield'].fillna(0, inplace=True)
        merged['Div_Daily_Yield'] = (1 + merged['Dividend Yield'] / 100) ** (1 / 252) - 1
        
        # 7. Calculate LSCDA Strategy
        # Logic:
        # If Regime == 1 (Risk On/Bull):
        #   Base = (Daily Price Return + Daily Div Yield)
        #   Strategy = 3 * Base
        #   (Note: standard leverage strategy usually borrows, so technically return is 3*(R_asset) - 2*(R_borrow). 
        #    If we assume R_borrow is close to 0 or ignored as per 'Cash-based' simplicity, we use 3*Total_Return)
        #   We use 'Simple_Ref' (Price Return) from analyzer to be sure we are adding dividend correctly. 
        #   analyzer's 'Total_Return_Daily' was just Price Return + 0.
        
        merged['Total_Return_Daily_with_Div'] = merged['Simple_Ref'] + merged['Div_Daily_Yield']
        
        # 3x Lev with Div
        merged['Lev_3x_Div_Daily'] = (3 * merged['Total_Return_Daily_with_Div']).clip(lower=-1.0)
        
        # Strategy Mixing
        # Regime 1: 3x Lev with Div
        # Regime 0: Small Cap (already Total Return usually)
        
        # User constraint: "3x (SC-based) you get dividend all the the time."
        # This implies adding Div_Daily_Yield to SC_Daily_Ret as well.
        merged['SC_Div_Daily'] = merged['SC_Daily_Ret'] + merged['Div_Daily_Yield']
        
        merged['LSCDA_Daily_Ret'] = np.where(merged['Regime'] == 1, 
                                             merged['Lev_3x_Div_Daily'], 
                                             merged['SC_Div_Daily'])
        
        # 8. Comparison Baselines
        # Benchmark: 3x (Cash-based) with Dividend. 
        # "when Regime is Risk off Leverage 3x (Cash-based) will not receive the dividend."
        # Regime 1: 3x (Price + Div)
        # Regime 0: Cash (0 return, 0 div)
        merged['Cash_Div_Daily_Ret'] = np.where(merged['Regime'] == 1,
                                                merged['Lev_3x_Div_Daily'],
                                                0.0)
        
        initial_capital = 10000
        merged['LSCDA_Growth'] = initial_capital * (1 + merged['LSCDA_Daily_Ret']).cumprod()
        merged['Cash_Div_Growth'] = initial_capital * (1 + merged['Cash_Div_Daily_Ret']).cumprod()
        
        # 9. Plotting
        plt.figure(figsize=(12, 6))
        
        # Plot Benchmark: 3x (Cash-based) + Div
        plt.plot(merged.index, merged['Cash_Div_Growth'], label='3x Strategy (Cash + Div)', linewidth=1, color='purple', alpha=0.7)
        
        # Plot LSCDA (Dividend Adjusted)
        plt.plot(merged.index, merged['LSCDA_Growth'], label='3x Strategy (Small Cap + Div)', linewidth=1.5, color='#10b981') # Emerald
        
        plt.yscale('log')
        plt.title('LSC vs LSCDA (Dividend Adjusted)')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value ($)')
        plt.legend()
        plt.grid(True, which="both", ls="-", alpha=0.2)
        
        output = io.BytesIO()
        plt.savefig(output, format='png')
        output.seek(0)
        plt.close()
        
        # 10. Table Data
        # Date, Regime, LSCDA Value, LSC Value, Div Yield (Daily approx), Div Yield (Annual)
        table_records = merged.sort_index(ascending=False)
        table_data = []
        
        for date, row in table_records.iterrows():
            regime = int(row['Regime']) if pd.notna(row['Regime']) else 0
            
            table_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'regime': regime,
                'val_lscda': f"{row['LSCDA_Growth']:,.2f}",
                'val_lsc': f"{row['Cash_Div_Growth']:,.2f}", # Reusing key 'val_lsc' but with new content to match usage? Better reset key.
                # Actually, app.py passes lscda_table to template. Template uses val_lscda and val_lsc.
                # I should update template too, but for now I can map 'val_lsc' to 'val_cash_div' effectively. 
                # Let's keep keys clear.
                'val_cash_div': f"{row['Cash_Div_Growth']:,.2f}",
                'formatted_div_yield': f"{row['Dividend Yield']:.2f}%" if pd.notna(row['Dividend Yield']) else "-"
            })
            
        return output, table_data

    except Exception as e:
        print(f"Error in analyze_lscda: {e}")
        traceback.print_exc()
        return None, []
