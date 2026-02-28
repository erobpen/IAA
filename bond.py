import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import traceback
import analyzer
import dividend_module
from plotting import save_plot_to_buffer

# Use Agg backend
matplotlib.use('Agg')

def analyze_bond():
    """
    Analyzes Leverage Bond strategy performance.
    Rotates to 3x S&P 500 when Regime=1, and to 10Y Treasury Bond when Regime=0.
    Calculates both without dividend and with dividend reinvested versions.
    
    Returns plot image and table data on an annual basis.
    """
    try:
        # 1. Get Daily Strategy Data
        daily_data = analyzer.get_strategy_data()
        if daily_data.empty:
            return None, []

        # 2. Get Dividend and Interest Rate Data (Shiller monthly)
        div_data = dividend_module.get_dividend_data()
        if div_data.empty:
            return None, []

        # 3. Merge data onto daily data by YearMonth
        daily_data['YearMonth'] = daily_data.index.to_period('M')
        div_data['YearMonth'] = div_data.index.to_period('M')

        df_daily = daily_data.reset_index()
        if 'Date' not in df_daily.columns:
            df_daily.rename(columns={df_daily.columns[0]: 'Date'}, inplace=True)

        df_div = div_data.reset_index()[['YearMonth', 'Dividend Yield', 'Long Interest Rate']]
        merged = pd.merge(df_daily, df_div, on='YearMonth', how='left')
        merged.set_index('Date', inplace=True)

        # 4. Calculate Daily Yields (Dividend and Bond)
        # Assuming missing data can be backfilled or just filled with 0
        merged['Dividend Yield'] = merged['Dividend Yield'].fillna(0)
        merged['Div_Daily_Yield'] = merged['Dividend Yield'] / 100 / 252
        
        merged['Long Interest Rate'] = merged['Long Interest Rate'].fillna(1.0) # Pre-1953 fallback for interest rates if any
        merged['Bond_Daily_Yield'] = merged['Long Interest Rate'] / 100 / 252

        # 5. ETF expense ratio
        ETF_EXPENSE_RATIO_DAILY = 0.01 / 252  # 1% annual -> daily

        # 6. Daily returns
        # 3x Strategy WITHOUT Dividends:
        #   Regime=1: 3x price - financing - expense
        #   Regime=0: 10Y Bond Yield
        merged['Lev_3x_NoDiv'] = (
            3 * merged['Simple_Ref']
            - merged['Financing_Rate_Daily']
            - ETF_EXPENSE_RATIO_DAILY
        ).clip(lower=-1.0)
        
        merged['Bond_Strategy_Daily'] = np.where(
            merged['Regime'] == 1,
            merged['Lev_3x_NoDiv'],
            merged['Bond_Daily_Yield']
        )

        # 3x Strategy WITH Dividends:
        #   Regime=1: 3x price + 1x div - financing - expense
        #   Regime=0: 10Y Bond Yield
        merged['Lev_3x_Div'] = (
            3 * merged['Simple_Ref']
            + merged['Div_Daily_Yield']
            - merged['Financing_Rate_Daily']
            - ETF_EXPENSE_RATIO_DAILY
        ).clip(lower=-1.0)

        merged['Bond_Strategy_Div_Daily'] = np.where(
            merged['Regime'] == 1,
            merged['Lev_3x_Div'],
            merged['Bond_Daily_Yield']
        )

        # 7. Cumulative growth (daily compounding)
        initial_capital = 10000.0
        merged['Total_Bond_Strategy'] = initial_capital * (1 + merged['Bond_Strategy_Daily']).cumprod()
        merged['Total_Bond_Strategy_Div'] = initial_capital * (1 + merged['Bond_Strategy_Div_Daily']).cumprod()

        # 8. Resample to annual for display
        annual = merged.resample('YE').last().copy()
        annual['Year'] = annual.index.year

        # Averages for display
        annual['Avg_Annual_Div_Yield'] = merged['Dividend Yield'].resample('YE').mean()
        annual['Avg_Annual_Bond_Yield'] = merged['Long Interest Rate'].resample('YE').mean()

        if annual.empty:
            return None, []

        # --- Plotting ---
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.semilogy(annual['Year'], annual['Total_Bond_Strategy'], label='3x Strategy (Bond)', color='#3b82f6', linewidth=2)
        ax.semilogy(annual['Year'], annual['Total_Bond_Strategy_Div'], label='3x Strategy (Bond + Div)', color='#eab308', linewidth=2)

        ax.set_title('Leverage Bond Strategy ($10k Initial)')
        ax.set_ylabel('Portfolio Value ($)')
        ax.set_xlabel('Year')
        ax.grid(True, which="both", ls="-", alpha=0.2)
        ax.legend()

        img = save_plot_to_buffer(fig)

        # --- Table Data ---
        table_records = annual.sort_values(by='Year', ascending=False)

        table_data = []
        years = table_records['Year'].astype(int).values
        total_strat = table_records['Total_Bond_Strategy'].values
        total_strat_div = table_records['Total_Bond_Strategy_Div'].values
        avg_divs = table_records['Avg_Annual_Div_Yield'].values
        avg_bonds = table_records['Avg_Annual_Bond_Yield'].values

        for i in range(len(table_records)):
            table_data.append({
                'year': int(years[i]),
                'total_strat': f"${total_strat[i]:,.0f}",
                'total_strat_div': f"${total_strat_div[i]:,.0f}",
                'div_yield': f"{avg_divs[i]:.2f}%" if pd.notna(avg_divs[i]) else "-",
                'bond_yield': f"{avg_bonds[i]:.2f}%" if pd.notna(avg_bonds[i]) else "-"
            })

        return img, table_data

    except Exception as e:
        print(f"Error in analyze_bond: {e}")
        traceback.print_exc()
        return None, []


def analyze_bond_filtered(start_date, end_date):
    """Re-run Bond analysis for a custom date range, re-compounding from $10k."""
    try:
        daily_data = analyzer.get_strategy_data()
        if daily_data.empty:
            return None

        div_data = dividend_module.get_dividend_data()
        if div_data.empty:
            return None

        daily_data['YearMonth'] = daily_data.index.to_period('M')
        div_data['YearMonth'] = div_data.index.to_period('M')

        df_daily = daily_data.reset_index()
        if 'Date' not in df_daily.columns:
            df_daily.rename(columns={df_daily.columns[0]: 'Date'}, inplace=True)

        df_div = div_data.reset_index()[['YearMonth', 'Dividend Yield', 'Long Interest Rate']]
        merged = pd.merge(df_daily, df_div, on='YearMonth', how='left')
        merged.set_index('Date', inplace=True)

        merged['Dividend Yield'] = merged['Dividend Yield'].fillna(0)
        merged['Div_Daily_Yield'] = merged['Dividend Yield'] / 100 / 252
        
        merged['Long Interest Rate'] = merged['Long Interest Rate'].fillna(1.0)
        merged['Bond_Daily_Yield'] = merged['Long Interest Rate'] / 100 / 252

        ETF_EXPENSE_RATIO_DAILY = 0.01 / 252

        merged['Lev_3x_NoDiv'] = (
            3 * merged['Simple_Ref']
            - merged['Financing_Rate_Daily']
            - ETF_EXPENSE_RATIO_DAILY
        ).clip(lower=-1.0)
        
        merged['Bond_Strategy_Daily'] = np.where(
            merged['Regime'] == 1,
            merged['Lev_3x_NoDiv'],
            merged['Bond_Daily_Yield']
        )

        merged['Lev_3x_Div'] = (
            3 * merged['Simple_Ref']
            + merged['Div_Daily_Yield']
            - merged['Financing_Rate_Daily']
            - ETF_EXPENSE_RATIO_DAILY
        ).clip(lower=-1.0)

        merged['Bond_Strategy_Div_Daily'] = np.where(
            merged['Regime'] == 1,
            merged['Lev_3x_Div'],
            merged['Bond_Daily_Yield']
        )

        # Slice to date range
        mask = (merged.index >= pd.Timestamp(start_date)) & (merged.index <= pd.Timestamp(end_date))
        window = merged.loc[mask]
        if window.empty or len(window) < 2:
            return None

        initial_capital = 10000.0
        total_strat = initial_capital * (1 + window['Bond_Strategy_Daily']).cumprod()
        total_strat_div = initial_capital * (1 + window['Bond_Strategy_Div_Daily']).cumprod()

        # Resample to annual for plotting
        annual_strat = total_strat.resample('YE').last()
        annual_strat_div = total_strat_div.resample('YE').last()
        years = annual_strat.index.year

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.semilogy(years, annual_strat.values, label='3x Strategy (Bond)', color='#3b82f6', linewidth=2)
        ax.semilogy(years, annual_strat_div.values, label='3x Strategy (Bond + Div)', color='#eab308', linewidth=2)

        ax.set_title(f'Leverage Bond Strategy: {years[0]}–{years[-1]} ($10k Initial)')
        ax.set_ylabel('Portfolio Value ($)')
        ax.set_xlabel('Year')
        ax.grid(True, which="both", ls="-", alpha=0.2)
        ax.legend()

        return save_plot_to_buffer(fig)
    except Exception as e:
        print(f"Error in analyze_bond_filtered: {e}")
        traceback.print_exc()
        return None
