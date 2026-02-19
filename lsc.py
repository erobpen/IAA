
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import traceback
import analyzer
import small_cap
from plotting import save_plot_to_buffer

def analyze_lsc():
    try:
        # 1. Get Daily Strategy Data (includes Regime and Date index)
        daily_data = analyzer.get_strategy_data()
        
        if daily_data.empty:
            return None, []

        # 2. Get Monthly Small Cap Data
        sc_data = small_cap.get_small_cap_data()
        
        if sc_data.empty:
            return None, []

        # 3. Preparation for Merge
        daily_data['YearMonth'] = daily_data.index.to_period('M')
        sc_data['YearMonth'] = sc_data.index.to_period('M')
        
        # Reset index for merging
        df_daily = daily_data.reset_index()
        
        # Ensure 'Date' column exists
        if 'Date' not in df_daily.columns:
            if 'index' in df_daily.columns:
                df_daily.rename(columns={'index': 'Date'}, inplace=True)
            else:
                 df_daily.rename(columns={df_daily.columns[0]: 'Date'}, inplace=True)

        df_sc = sc_data.reset_index()[['YearMonth', 'Small_Value_Ret']]
        
        merged = pd.merge(df_daily, df_sc, on='YearMonth', how='left')
        merged.set_index('Date', inplace=True)
        
        # 4. Calculate Daily Equivalent Return for Small Cap
        trading_days_per_month = merged.groupby('YearMonth')['Close'].count()
        trading_days_per_month.name = 'TradingDays'
        
        merged = pd.merge(merged.reset_index(), trading_days_per_month, on='YearMonth', how='left')
        merged.set_index('Date', inplace=True)
        
        # Handle NaNs
        merged['Small_Value_Ret'] = merged['Small_Value_Ret'].fillna(0)
        merged['TradingDays'] = merged['TradingDays'].fillna(21)

        # Avoid division by zero
        merged['TradingDays'] = merged['TradingDays'].replace(0, 1)

        merged['SC_Daily_Ret'] = (1 + merged['Small_Value_Ret']) ** (1 / merged['TradingDays']) - 1
        
        # 5. Calculate LSC Strategy
        # 3x leveraged ETF cost model: 3×price − 2×financing − expense
        # financing_rate and expense_ratio apply only when holding the 3x ETF (Regime=1).
        # Financing_Rate_Daily comes from analyzer (Fed Funds Rate from FRED).
        ETF_EXPENSE_RATIO_DAILY = 0.01 / 252  # 1% annual -> daily
        lev_ret = (
            merged['Total_Return_Daily'] * 3
            - merged['Financing_Rate_Daily']
            - ETF_EXPENSE_RATIO_DAILY
        ).clip(lower=-1.0)
        
        merged['LSC_Daily_Ret'] = np.where(merged['Regime'] == 1, lev_ret, merged['SC_Daily_Ret'])
        
        # 6. Calculate Cumulative Growth
        initial_capital = 10000
        merged['LSC_Growth'] = initial_capital * (1 + merged['LSC_Daily_Ret']).cumprod()
        
        # 7. Plotting
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(merged.index, merged['Lev_3x_Growth'], label='3x Strategy (Cash)', linewidth=1, color='purple', alpha=0.7)
        ax.plot(merged.index, merged['LSC_Growth'], label='3x Strategy (Small Cap)', linewidth=1.5, color='#d946ef')
        
        ax.set_yscale('log')
        ax.set_title('Leverage Strategy: Cash vs Small Cap (Risk Off)')
        ax.set_xlabel('Date')
        ax.set_ylabel('Portfolio Value ($)')
        ax.legend()
        ax.grid(True, which="both", ls="-", alpha=0.2)
        
        output = save_plot_to_buffer(fig)
        
        # 8. Table Data (vectorized)
        table_records = merged.sort_index(ascending=False)
        
        table_data = []
        dates = table_records.index.strftime('%Y-%m-%d')
        regime_vals = table_records['Regime'].values
        cash_vals = table_records['Lev_3x_Growth'].values
        sc_vals = table_records['LSC_Growth'].values
        sc_daily_vals = table_records['SC_Daily_Ret'].values
        
        for i in range(len(table_records)):
            regime = int(regime_vals[i]) if pd.notna(regime_vals[i]) else 0
            
            table_data.append({
                'date': dates[i],
                'regime': regime,
                'val_cash': f"{cash_vals[i]:,.2f}",
                'val_sc': f"{sc_vals[i]:,.2f}",
                'sc_daily_yield': f"{sc_daily_vals[i]*100:.4f}%"
            })
            
        return output, table_data

    except Exception as e:
        print(f"Error in analyze_lsc: {e}")
        traceback.print_exc()
        return None, []

if __name__ == "__main__":
    analyze_lsc()


def analyze_lsc_filtered(start_date, end_date):
    """Re-run LSC analysis for a custom date range, re-compounding from $10k."""
    try:
        daily_data = analyzer.get_strategy_data()
        if daily_data.empty:
            return None

        sc_data = small_cap.get_small_cap_data()
        if sc_data.empty:
            return None

        # Same merge logic as analyze_lsc
        daily_data['YearMonth'] = daily_data.index.to_period('M')
        sc_data['YearMonth'] = sc_data.index.to_period('M')

        df_daily = daily_data.reset_index()
        if 'Date' not in df_daily.columns:
            if 'index' in df_daily.columns:
                df_daily.rename(columns={'index': 'Date'}, inplace=True)
            else:
                df_daily.rename(columns={df_daily.columns[0]: 'Date'}, inplace=True)

        df_sc = sc_data.reset_index()[['YearMonth', 'Small_Value_Ret']]
        merged = pd.merge(df_daily, df_sc, on='YearMonth', how='left')
        merged.set_index('Date', inplace=True)

        trading_days_per_month = merged.groupby('YearMonth')['Close'].count()
        trading_days_per_month.name = 'TradingDays'
        merged = pd.merge(merged.reset_index(), trading_days_per_month, on='YearMonth', how='left')
        merged.set_index('Date', inplace=True)

        merged['Small_Value_Ret'] = merged['Small_Value_Ret'].fillna(0)
        merged['TradingDays'] = merged['TradingDays'].fillna(21).replace(0, 1)
        merged['SC_Daily_Ret'] = (1 + merged['Small_Value_Ret']) ** (1 / merged['TradingDays']) - 1

        ETF_EXPENSE_RATIO_DAILY = 0.01 / 252
        lev_ret = (
            merged['Total_Return_Daily'] * 3 - merged['Financing_Rate_Daily'] - ETF_EXPENSE_RATIO_DAILY
        ).clip(lower=-1.0)
        merged['LSC_Daily_Ret'] = np.where(merged['Regime'] == 1, lev_ret, merged['SC_Daily_Ret'])
        merged['Cash_Daily_Ret'] = np.where(merged['Regime'] == 1, lev_ret, 0.0)

        # Slice to date range
        mask = (merged.index >= pd.Timestamp(start_date)) & (merged.index <= pd.Timestamp(end_date))
        window = merged.loc[mask]
        if window.empty or len(window) < 2:
            return None

        initial_capital = 10000
        cash_growth = initial_capital * (1 + window['Cash_Daily_Ret']).cumprod()
        lsc_growth = initial_capital * (1 + window['LSC_Daily_Ret']).cumprod()

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(window.index, cash_growth, label='3x Strategy (Cash)', linewidth=1, color='purple', alpha=0.7)
        ax.plot(window.index, lsc_growth, label='3x Strategy (Small Cap)', linewidth=1.5, color='#d946ef')

        ax.set_yscale('log')
        start_yr = window.index[0].strftime('%Y')
        end_yr = window.index[-1].strftime('%Y')
        ax.set_title(f'LSC Strategy: {start_yr}–{end_yr} ($10k Initial)')
        ax.set_xlabel('Date')
        ax.set_ylabel('Portfolio Value ($)')
        ax.legend()
        ax.grid(True, which="both", ls="-", alpha=0.2)

        return save_plot_to_buffer(fig)
    except Exception as e:
        print(f"Error in analyze_lsc_filtered: {e}")
        traceback.print_exc()
        return None
