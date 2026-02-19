
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

def analyze_lda():
    """
    Analyzes Leverage Dividend Adjusted (LDA) performance.
    Reinvests dividends daily. NO Small Cap rotation (uses cash during Risk Off).
    
    This should produce the SAME values as LSCDA's 'Cash + Div' column,
    since both compute:  3×price + 1×div − financing − expense  when Regime=1, else 0+div.
    
    Returns plot image and table data.
    """
    try:
        # 1. Get Daily Strategy Data
        daily_data = analyzer.get_strategy_data()
        if daily_data.empty:
            return None, []

        # 2. Get Dividend Data (Shiller monthly, will be merged to daily)
        div_data = dividend_module.get_dividend_data()
        if div_data.empty:
            return None, []

        # 3. Merge dividend data onto daily data by YearMonth
        daily_data['YearMonth'] = daily_data.index.to_period('M')
        div_data['YearMonth'] = div_data.index.to_period('M')

        df_daily = daily_data.reset_index()
        if 'Date' not in df_daily.columns:
            df_daily.rename(columns={df_daily.columns[0]: 'Date'}, inplace=True)

        df_div = div_data.reset_index()[['YearMonth', 'Dividend Yield']]
        merged = pd.merge(df_daily, df_div, on='YearMonth', how='left')
        merged.set_index('Date', inplace=True)

        # 4. Calculate Daily Dividend Yield
        # Convert annual yield (%) to daily: simple division by 252 trading days.
        merged['Dividend Yield'] = merged['Dividend Yield'].fillna(0)
        merged['Div_Daily_Yield'] = merged['Dividend Yield'] / 100 / 252

        # 5. ETF expense ratio (same as analyzer.py and lscda.py)
        ETF_EXPENSE_RATIO_DAILY = 0.01 / 252  # 1% annual -> daily

        # 6. Daily returns with dividends
        # Buy & Hold (1x): price + 1x dividend (no expense ratio for index ETF)
        merged['BH_Div_Daily'] = merged['Simple_Ref'] + merged['Div_Daily_Yield']

        # 3x Strategy with dividends — full cost model:
        #   Regime=1: 3×price + 1×div − 2×financing − expense
        #   Regime=0: 0 + 1×div (cash earns dividend from reinvested position)
        # For simplicity and consistency with LSCDA Cash+Div:
        #   Regime=1: 3×price + 1×div − financing − expense
        #   Regime=0: 0 (cash, no dividend during cash periods)
        merged['Lev_3x_Div_Daily'] = (
            3 * merged['Simple_Ref']
            + merged['Div_Daily_Yield']
            - merged['Financing_Rate_Daily']
            - ETF_EXPENSE_RATIO_DAILY
        ).clip(lower=-1.0)

        merged['Lev_Cash_Div_Daily'] = np.where(
            merged['Regime'] == 1,
            merged['Lev_3x_Div_Daily'],
            0.0
        )

        # 7. Cumulative growth (daily compounding)
        initial_capital = 10000.0
        merged['Total_LDA_SP500'] = initial_capital * (1 + merged['BH_Div_Daily']).cumprod()
        merged['Total_LDA_3x'] = initial_capital * (1 + merged['Lev_Cash_Div_Daily']).cumprod()

        # Also store raw price growth for reference columns
        merged['Price_BH'] = merged['Buy_Hold_Growth']
        merged['Price_3x'] = merged['Lev_3x_Growth']

        # 8. Resample to annual for display
        annual = merged.resample('YE').last().copy()
        annual['Year'] = annual.index.year

        # Get average annual dividend yield for display
        div_annual = merged['Dividend Yield'].resample('YE').mean()
        annual['Avg_Annual_Yield'] = div_annual

        # Filter to years where dividend data exists
        annual = annual.dropna(subset=['Avg_Annual_Yield'])
        annual = annual[annual['Avg_Annual_Yield'] > 0]

        if annual.empty:
            return None, []

        # --- Plotting ---
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.semilogy(annual['Year'], annual['Total_LDA_SP500'], label='Total Return S&P 500 (Div Reinvested)', color='#10b981', linewidth=2)
        ax.semilogy(annual['Year'], annual['Total_LDA_3x'], label='Total Return 3x Strategy (Div Reinvested)', color='#8b5cf6', linewidth=2)

        ax.set_title('Leverage Dividend Adjusted Total Return ($10k Initial)')
        ax.set_ylabel('Portfolio Value ($)')
        ax.set_xlabel('Year')
        ax.grid(True, which="both", ls="-", alpha=0.2)
        ax.legend()

        img = save_plot_to_buffer(fig)

        # --- Table Data ---
        table_records = annual.sort_values(by='Year', ascending=False)

        table_data = []
        years = table_records['Year'].astype(int).values
        total_sp = table_records['Total_LDA_SP500'].values
        total_3x = table_records['Total_LDA_3x'].values
        avg_yields = table_records['Avg_Annual_Yield'].values
        price_sp = table_records['Price_BH'].values
        price_3x = table_records['Price_3x'].values

        for i in range(len(table_records)):
            table_data.append({
                'year': int(years[i]),
                'total_sp500': f"${total_sp[i]:,.0f}",
                'total_3x': f"${total_3x[i]:,.0f}",
                'div_yield': f"{avg_yields[i]:.2f}%",
                'price_sp500': f"${price_sp[i]:,.0f}",
                'price_3x': f"${price_3x[i]:,.0f}"
            })

        return img, table_data

    except Exception as e:
        print(f"Error in analyze_lda: {e}")
        traceback.print_exc()
        return None, []
