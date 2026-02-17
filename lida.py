
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import io
import analyzer
import database

# Use Agg backend
matplotlib.use('Agg')

def analyze_lida():
    """
    Analyzes Leverage and Dividend Adjusted (LIDA) performance.
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
        # Resample to Annual End-Of-Year
        strat_annual = strat_df.resample('A').last()
        strat_annual['Year'] = strat_annual.index.year
        
        # Calculate Annual Price Return Factor
        strat_annual['BH_Price_Change'] = strat_annual['Buy_Hold_Growth'].pct_change()
        strat_annual['Lev_Price_Change'] = strat_annual['Lev_3x_Growth'].pct_change()
        
        # B. Dividends (Yield)
        # Calculate Monthly Yield in mkt_df first
        mkt_df['Div_Yield'] = mkt_df['Dividend'] / mkt_df['SP500']
        # Resample to Annual Average Yield
        div_annual = mkt_df['Div_Yield'].resample('A').mean().to_frame(name='Avg_Annual_Yield')
        div_annual['Year'] = div_annual.index.year
        
        # --- Merge ---
        merged = pd.merge(strat_annual, div_annual, on='Year', how='inner')
        
        if merged.empty:
            return None, []
            
        # --- Logic: Reinvestment (No Inflation) ---
        
        # Initialize Simulation
        initial_capital = 10000.0
        
        # Let's loop
        merged = merged.sort_values('Year')
        
        bh_vals = []
        lev_vals = []
        
        curr_bh = initial_capital
        curr_lev = initial_capital
        
        for i, row in merged.iterrows():
            # Price Change (Growth)
            pct_bh = row['BH_Price_Change'] if pd.notna(row['BH_Price_Change']) else 0.0
            pct_lev = row['Lev_Price_Change'] if pd.notna(row['Lev_Price_Change']) else 0.0
            
            # Dividend Yield
            div_y = row['Avg_Annual_Yield'] if pd.notna(row['Avg_Annual_Yield']) else 0.0
            
            # Total Return
            curr_bh = curr_bh * (1 + pct_bh + div_y)
            # Assuming 1x dividend yield reinvested for 3x strategy as well
            curr_lev = curr_lev * (1 + pct_lev + div_y) 
            
            bh_vals.append(curr_bh)
            lev_vals.append(curr_lev)
            
        merged['Total_LIDA_SP500'] = bh_vals
        merged['Total_LIDA_3x'] = lev_vals
        
        # --- Plotting ---
        plt.figure(figsize=(10, 6))
        plt.semilogy(merged['Year'], merged['Total_LIDA_SP500'], label='Total Return S&P 500 (Div Reinvested)', color='#10b981', linewidth=2)
        plt.semilogy(merged['Year'], merged['Total_LIDA_3x'], label='Total Return 3x Strategy (Div Reinvested)', color='#8b5cf6', linewidth=2)
        
        plt.title('LIDA Total Return Performance ($10k Initial)')
        plt.ylabel('Portfolio Value ($)')
        plt.xlabel('Year')
        plt.grid(True, which="both", ls="-", alpha=0.2)
        plt.legend()
        
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        plt.close()
        
        # --- Table Data ---
        table_records = merged.sort_values(by='Year', ascending=False)
        table_data = []
        
        for _, row in table_records.iterrows():
            table_data.append({
                'year': int(row['Year']),
                'total_sp500': f"${row['Total_LIDA_SP500']:,.0f}",
                'total_3x': f"${row['Total_LIDA_3x']:,.0f}",
                'div_yield': f"{row['Avg_Annual_Yield']*100:.2f}%",
                # Nominal Price Return (Reference)
                'price_sp500': f"${row['Buy_Hold_Growth']:,.0f}",
                'price_3x': f"${row['Lev_3x_Growth']:,.0f}"
            })
            
        return img, table_data

    except Exception as e:
        print(f"Error in analyze_lida: {e}")
        import traceback
        traceback.print_exc()
        return None, []
