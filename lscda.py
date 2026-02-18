
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import traceback
import analyzer
import small_cap
import dividend_module
from plotting import save_plot_to_buffer

def analyze_lscda():
    try:
        # 1. Get Daily Strategy Data
        daily_data = analyzer.get_strategy_data()
        
        if daily_data.empty:
            return None, []

        # 2. Get Monthly Small Cap Data
        sc_data = small_cap.get_small_cap_data()

        # 3. Get Dividend Data
        div_data = dividend_module.get_dividend_data()

        if sc_data.empty or div_data.empty:
            print("Warning: Missing SC or Dividend data.")
            return None, []

        # 4. Merge Data
        daily_data['YearMonth'] = daily_data.index.to_period('M')
        sc_data['YearMonth'] = sc_data.index.to_period('M')
        div_data['YearMonth'] = div_data.index.to_period('M')

        df_daily = daily_data.reset_index()
        if 'Date' not in df_daily.columns:
             df_daily.rename(columns={df_daily.columns[0]: 'Date'}, inplace=True)

        df_sc = sc_data.reset_index()[['YearMonth', 'Small_Value_Ret']]
        df_div = div_data.reset_index()[['YearMonth', 'Dividend Yield']]

        # Merge Daily + SC
        merged = pd.merge(df_daily, df_sc, on='YearMonth', how='left')
        
        # Merge + Div
        merged = pd.merge(merged, df_div, on='YearMonth', how='left')
        
        merged.set_index('Date', inplace=True)
        
        # 5. Calculate Daily SC Return (Same as LSC)
        trading_days = merged.groupby('YearMonth')['Close'].transform('count')
        merged['TradingDays'] = trading_days.fillna(21).replace(0, 1)
        
        merged['Small_Value_Ret'] = merged['Small_Value_Ret'].fillna(0)
        merged['SC_Daily_Ret'] = (1 + merged['Small_Value_Ret']) ** (1 / merged['TradingDays']) - 1
        
        # 6. Calculate Daily Dividend Yield
        merged['Dividend Yield'] = merged['Dividend Yield'].fillna(0)
        merged['Div_Daily_Yield'] = (1 + merged['Dividend Yield'] / 100) ** (1 / 252) - 1
        
        # 7. Calculate LSCDA Strategy
        merged['Total_Return_Daily_with_Div'] = merged['Simple_Ref'] + merged['Div_Daily_Yield']
        
        # 3x Lev with Div
        merged['Lev_3x_Div_Daily'] = (3 * merged['Total_Return_Daily_with_Div']).clip(lower=-1.0)
        
        # Strategy Mixing
        merged['SC_Div_Daily'] = merged['SC_Daily_Ret'] + merged['Div_Daily_Yield']
        
        merged['LSCDA_Daily_Ret'] = np.where(merged['Regime'] == 1, 
                                             merged['Lev_3x_Div_Daily'], 
                                             merged['SC_Div_Daily'])
        
        # 8. Comparison Baselines
        merged['Cash_Div_Daily_Ret'] = np.where(merged['Regime'] == 1,
                                                merged['Lev_3x_Div_Daily'],
                                                0.0)
        
        initial_capital = 10000
        merged['LSCDA_Growth'] = initial_capital * (1 + merged['LSCDA_Daily_Ret']).cumprod()
        merged['Cash_Div_Growth'] = initial_capital * (1 + merged['Cash_Div_Daily_Ret']).cumprod()
        
        # 9. Plotting
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(merged.index, merged['Cash_Div_Growth'], label='3x Strategy (Cash + Div)', linewidth=1, color='purple', alpha=0.7)
        ax.plot(merged.index, merged['LSCDA_Growth'], label='3x Strategy (Small Cap + Div)', linewidth=1.5, color='#10b981')
        
        ax.set_yscale('log')
        ax.set_title('LSC vs LSCDA (Dividend Adjusted)')
        ax.set_xlabel('Date')
        ax.set_ylabel('Portfolio Value ($)')
        ax.legend()
        ax.grid(True, which="both", ls="-", alpha=0.2)
        
        output = save_plot_to_buffer(fig)
        
        # 10. Table Data (vectorized)
        table_records = merged.sort_index(ascending=False)
        
        table_data = []
        dates = table_records.index.strftime('%Y-%m-%d')
        regime_vals = table_records['Regime'].values
        lscda_vals = table_records['LSCDA_Growth'].values
        cash_div_vals = table_records['Cash_Div_Growth'].values
        div_yield_vals = table_records['Dividend Yield'].values
        
        for i in range(len(table_records)):
            regime = int(regime_vals[i]) if pd.notna(regime_vals[i]) else 0
            div_str = f"{div_yield_vals[i]:.2f}%" if pd.notna(div_yield_vals[i]) else "-"
            
            table_data.append({
                'date': dates[i],
                'regime': regime,
                'val_lscda': f"{lscda_vals[i]:,.2f}",
                'val_lsc': f"{cash_div_vals[i]:,.2f}",
                'val_cash_div': f"{cash_div_vals[i]:,.2f}",
                'formatted_div_yield': div_str
            })
            
        return output, table_data

    except Exception as e:
        print(f"Error in analyze_lscda: {e}")
        traceback.print_exc()
        return None, []
