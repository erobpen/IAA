
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import traceback
import analyzer
import database
from plotting import save_plot_to_buffer

# Use Agg backend
matplotlib.use('Agg')

def analyze_lda():
    """
    Analyzes Leverage Dividend Adjusted (LDA) performance.
    Reinvests annual dividends. NO Inflation adjustment.
    Returns plot image and table data.
    """
    try:
        # 1. Get Strategy Data (Daily) - Provides Price Growth
        strat_df = analyzer.get_strategy_data()
        if strat_df.empty:
            return None, []
            
        # 2. Get Market Stats (Shiller) for Dividends
        mkt_df = database.get_all_market_stats()
        if mkt_df.empty:
            return None, []
            
        # --- Process Data (Annualize) ---
        
        # A. Strategy Growth (Price Return)
        strat_annual = strat_df.resample('A').last()
        strat_annual['Year'] = strat_annual.index.year
        
        # Calculate Annual Price Return Factor
        strat_annual['BH_Price_Change'] = strat_annual['Buy_Hold_Growth'].pct_change()
        strat_annual['Lev_Price_Change'] = strat_annual['Lev_3x_Growth'].pct_change()
        
        # B. Dividends (Yield)
        mkt_df['Div_Yield'] = mkt_df['Dividend'] / mkt_df['SP500']
        div_annual = mkt_df['Div_Yield'].resample('A').mean().to_frame(name='Avg_Annual_Yield')
        div_annual['Year'] = div_annual.index.year
        
        # --- Merge ---
        merged = pd.merge(strat_annual, div_annual, on='Year', how='inner')
        
        if merged.empty:
            return None, []
            
        # --- Logic: Reinvestment (No Inflation) ---
        initial_capital = 10000.0
        
        merged = merged.sort_values('Year')
        
        # Vectorized simulation using numpy arrays
        bh_changes = merged['BH_Price_Change'].fillna(0).values
        lev_changes = merged['Lev_Price_Change'].fillna(0).values
        div_yields = merged['Avg_Annual_Yield'].fillna(0).values
        
        bh_vals = np.empty(len(merged))
        lev_vals = np.empty(len(merged))
        
        curr_bh = initial_capital
        curr_lev = initial_capital
        
        for i in range(len(merged)):
            # Buy & Hold (1x index): earns 1x dividend. Index ETF fee (~0.06%) disregarded.
            curr_bh = curr_bh * (1 + bh_changes[i] + div_yields[i])
            # 3x Leveraged ETF (e.g., SPXL): earns 3x dividend because it holds 3x the shares.
            # The 1% annual ETF expense ratio is already embedded in lev_changes
            # (comes from analyzer's Lev_3x_Growth which deducts expense daily).
            curr_lev = curr_lev * (1 + lev_changes[i] + 3 * div_yields[i])
            bh_vals[i] = curr_bh
            lev_vals[i] = curr_lev
            
        merged['Total_LDA_SP500'] = bh_vals
        merged['Total_LDA_3x'] = lev_vals
        
        # --- Plotting ---
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.semilogy(merged['Year'], merged['Total_LDA_SP500'], label='Total Return S&P 500 (Div Reinvested)', color='#10b981', linewidth=2)
        ax.semilogy(merged['Year'], merged['Total_LDA_3x'], label='Total Return 3x Strategy (Div Reinvested)', color='#8b5cf6', linewidth=2)
        
        ax.set_title('Leverage Dividend Adjusted Total Return ($10k Initial)')
        ax.set_ylabel('Portfolio Value ($)')
        ax.set_xlabel('Year')
        ax.grid(True, which="both", ls="-", alpha=0.2)
        ax.legend()
        
        img = save_plot_to_buffer(fig)
        
        # --- Table Data (vectorized) ---
        table_records = merged.sort_values(by='Year', ascending=False)
        
        table_data = []
        years = table_records['Year'].astype(int).values
        total_sp = table_records['Total_LDA_SP500'].values
        total_3x = table_records['Total_LDA_3x'].values
        avg_yields = table_records['Avg_Annual_Yield'].values
        price_sp = table_records['Buy_Hold_Growth'].values
        price_3x = table_records['Lev_3x_Growth'].values
        
        for i in range(len(table_records)):
            table_data.append({
                'year': int(years[i]),
                'total_sp500': f"${total_sp[i]:,.0f}",
                'total_3x': f"${total_3x[i]:,.0f}",
                'div_yield': f"{avg_yields[i]*100:.2f}%",
                'price_sp500': f"${price_sp[i]:,.0f}",
                'price_3x': f"${price_3x[i]:,.0f}"
            })
            
        return img, table_data

    except Exception as e:
        print(f"Error in analyze_lda: {e}")
        traceback.print_exc()
        return None, []
