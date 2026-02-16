
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
    Analyzes Leverage Inflation and Dividend Adjusted (LIDA) performance.
    Reinvests annual dividends and adjusts for inflation.
    Returns plot image and table data.
    """
    try:
        # 1. Get Strategy Data (Daily) - Provides Price Growth
        strat_df = analyzer.get_strategy_data()
        if strat_df.empty:
            return None, []
            
        # 2. Get Inflation Data (Monthly/Annual)
        inf_df = database.get_all_inflation_data()
        if inf_df.empty:
            return None, []
            
        # 3. Get Market Stats (Shiller) for Dividends
        mkt_df = database.get_all_market_stats()
        if mkt_df.empty:
            return None, []
            
        # --- Process Data (Annualize) ---
        
        # A. Strategy Growth (Price Return)
        # Resample to Annual End-Of-Year
        strat_annual = strat_df.resample('A').last()
        strat_annual['Year'] = strat_annual.index.year
        
        # Calculate Annual Price Return Factor
        # Growth_Factor_t = Value_t / Value_{t-1}
        # But we have cumulative growth columns: 'Buy_Hold_Growth', 'Lev_3x_Growth'
        # We can calculate the year-over-year change of these cumulative values to get the annual return multiplier.
        strat_annual['BH_Price_Change'] = strat_annual['Buy_Hold_Growth'].pct_change()
        strat_annual['Lev_Price_Change'] = strat_annual['Lev_3x_Growth'].pct_change()
        
        # First year is NaN, fill with (Value / Initial) - 1 ??
        # Or just start from the second year. LIA logic usually starts 1928.
        # Let's trust pct_change for now, first row will be NaN.
        
        # B. Dividends (Yield)
        # Calculate Monthly Yield in mkt_df first
        mkt_df['Div_Yield'] = mkt_df['Dividend'] / mkt_df['SP500']
        # Resample to Annual Average Yield
        # User said: "calculate dividend average per year before 'reinvesing it' only once per year"
        div_annual = mkt_df['Div_Yield'].resample('A').mean().to_frame(name='Avg_Annual_Yield')
        div_annual['Year'] = div_annual.index.year
        
        # C. Inflation
        inf_annual = inf_df.resample('A').last()
        inf_annual['Year'] = inf_annual.index.year
        
        # --- Merge ---
        merged = pd.merge(strat_annual, div_annual, on='Year', how='inner')
        merged = pd.merge(merged, inf_annual[['CPI', 'Year']], on='Year', how='inner')
        # Merge resets index? 'Year' is a column not index in merge result usually if on='Year'
        
        if merged.empty:
            return None, []
            
        # --- Logic: Reinvestment + Inflation ---
        
        # Initialize Simulation
        initial_capital = 10000.0
        
        # We need to simulate the path year by year
        # Total_Return_bh = (1 + Price_Change + Div_Yield)
        # Total_Return_lev = (1 + Lev_Price_Change + (Div_Yield * 3 ??)) 
        # Wait, simple Simulation:
        # S&P 500: Reinvest dividends.
        # 3x Strategy: Does it get 3x dividends?
        # Usually leveraged ETFs pay dividends (minus expense ratios), potentially magnified or absorbed.
        # User said: "recalculate if yearly dividend yield is reinvested into each"
        # Since it's a "Real 3x Strategy", let's assume we reinvest the dividend yield into the strategy.
        # However, 3x leverage usually implies borrowing costs. `analyzer.py` calculates daily 3x return clips.
        # Simple interpretation: Add the annual yield to the annual strategy return.
        # Does 3x leverage get 3x dividends? No, usually you pay interest on margin.
        # PROBABLY NOT 3x DIVIDENDS. The dividend yield is on the underlying asset.
        # If you hold UPRO (3x SPY), the dividend yield is roughly 0 or very low because it's consumed by swap costs/fees.
        # BUT, for a theoretical "3x Strategy" simulation requested by user, checking the prompt: "if yearly dividend yield is reinvested into each".
        # It's ambiguous if 3x gets 3x yield.
        # Safest assumption: Add 1x yield to both. (Conservative).
        # OR: If user implies "Adjusted", maybe add yield to the base return before leveraging?
        # Let's stick to: Price_Return_3x + 1x_Yield.
        # Rationale: Dividends are cash. You get the cash and buy more strategy units.
        
        # Let's loop
        merged = merged.sort_values('Year')
        
        bh_vals = []
        lev_vals = []
        
        curr_bh = initial_capital
        curr_lev = initial_capital
        
        # Inflation base
        base_cpi = merged['CPI'].iloc[0]
        
        for i, row in merged.iterrows():
            # Price Change (Growth)
            # Handle first year manually or if NaN
            pct_bh = row['BH_Price_Change'] if pd.notna(row['BH_Price_Change']) else 0.0
            pct_lev = row['Lev_Price_Change'] if pd.notna(row['Lev_Price_Change']) else 0.0
            
            # Dividend Yield
            div_y = row['Avg_Annual_Yield'] if pd.notna(row['Avg_Annual_Yield']) else 0.0
            
            # Total Return
            # Reinvest: Value * (1 + Price_Change + Div_Yield)
            # Approximation of Total Return = Price Return + Dividend Yield
            
            curr_bh = curr_bh * (1 + pct_bh + div_y)
            curr_lev = curr_lev * (1 + pct_lev + div_y) # Assuming 1x dividend yield reinvested
            
            bh_vals.append(curr_bh)
            lev_vals.append(curr_lev)
            
        merged['Nominal_LIDA_SP500'] = bh_vals
        merged['Nominal_LIDA_3x'] = lev_vals
        
        # Adjust for Inflation
        merged['Cumulative_Inflation'] = merged['CPI'] / base_cpi
        
        merged['Real_LIDA_SP500'] = merged['Nominal_LIDA_SP500'] / merged['Cumulative_Inflation']
        merged['Real_LIDA_3x'] = merged['Nominal_LIDA_3x'] / merged['Cumulative_Inflation']
        
        # --- Plotting ---
        plt.figure(figsize=(10, 6))
        plt.semilogy(merged['Year'], merged['Real_LIDA_SP500'], label='Real S&P 500 (Div+Inf Adj)', color='#10b981', linewidth=2)
        plt.semilogy(merged['Year'], merged['Real_LIDA_3x'], label='Real 3x Strategy (Div+Inf Adj)', color='#8b5cf6', linewidth=2)
        
        plt.title('LIDA Real Performance ($10k Initial)')
        plt.ylabel('Real Value ($)')
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
                'real_sp500': f"${row['Real_LIDA_SP500']:,.0f}",
                'real_3x': f"${row['Real_LIDA_3x']:,.0f}",
                'inflation_factor': f"{row['Cumulative_Inflation']:.2f}x",
                'div_yield': f"{row['Avg_Annual_Yield']*100:.2f}%",
                'nominal_sp500': f"${row['Nominal_LIDA_SP500']:,.0f}",
                'nominal_3x': f"${row['Nominal_LIDA_3x']:,.0f}"
            })
            
        return img, table_data

    except Exception as e:
        print(f"Error in analyze_lida: {e}")
        import traceback
        traceback.print_exc()
        return None, []
