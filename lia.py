import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import analyzer
import database

def analyze_lia():
    """
    Analyzes Leverage Inflation Adjusted (LIA) performance.
    Returns plot image and table data.
    """
    try:
        # 1. Get Strategy Data (Daily)
        strat_df = analyzer.get_strategy_data()
        if strat_df.empty:
            return None, []
            
        # 2. Get Inflation Data (Monthly/Annual)
        inf_df = database.get_all_inflation_data()
        if inf_df.empty:
            return None, []
            
        # 3. Process Data
        # We need End-Of-Year data for both.
        
        # Resample Strategy Data to Annual (taking the last value of each year)
        strat_annual = strat_df.resample('A').last()
        
        # Resample Inflation Data to Annual (taking the last value of each year)
        # Verify inflation date index. It should be usually monthly.
        inf_annual = inf_df.resample('A').last()
        
        # Merge on Year
        # Create a common Year column or index
        strat_annual['Year'] = strat_annual.index.year
        inf_annual['Year'] = inf_annual.index.year
        
        # Merge
        merged = pd.merge(strat_annual, inf_annual[['CPI', 'Year']], on='Year', how='inner')
        
        if merged.empty:
            return None, []
        
        # 4. Calculate Real Values
        # Formula: Real Value = Nominal Value / (Current CPI / Base CPI)
        # Wait, simple adjustment: Capital_Real_t = Capital_Nominal_t / Cumulative_Inflation_Factor_t
        # Cumulative Factor_t = CPI_t / CPI_start
        
        base_cpi = merged['CPI'].iloc[0]
        merged['Cumulative_Inflation'] = merged['CPI'] / base_cpi
        
        merged['Real_SP500'] = merged['Buy_Hold_Growth'] / merged['Cumulative_Inflation']
        merged['Real_Strategy_3x'] = merged['Lev_3x_Growth'] / merged['Cumulative_Inflation']
        
        # 5. Plotting
        plt.figure(figsize=(10, 6))
        # Using Semilog
        plt.semilogy(merged['Year'], merged['Real_SP500'], label='Real S&P 500 (Inf. Adj.)', color='#94a3b8', linewidth=2)
        plt.semilogy(merged['Year'], merged['Real_Strategy_3x'], label='Real 3x Strategy (Inf. Adj.)', color='#f97316', linewidth=2)
        
        plt.title('Inflation Adjusted Performance (Year-End) - $10k Initial (1928)')
        plt.ylabel('Real Portfolio Value ($1928)')
        plt.xlabel('Year')
        plt.grid(True, which="both", ls="-", alpha=0.2)
        plt.legend()
        
        # Set background color to match app theme
        # User requested to match other tabs (which are standard white)
        
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        plt.close()
        
        # 6. Prepare Table Data
        # Reverse order for table
        table_records = merged.sort_values(by='Year', ascending=False)
        
        table_data = []
        for _, row in table_records.iterrows():
            table_data.append({
                'year': int(row['Year']),
                'real_sp500': f"${row['Real_SP500']:,.0f}",
                'real_3x': f"${row['Real_Strategy_3x']:,.0f}",
                'inflation_factor': f"{row['Cumulative_Inflation']:.2f}x",
                'nominal_sp500': f"${row['Buy_Hold_Growth']:,.0f}",
                'nominal_3x': f"${row['Lev_3x_Growth']:,.0f}"
            })
            
        return img, table_data

    except Exception as e:
        print(f"Error in analyze_lia: {e}")
        return None, []
