
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import traceback
import dividend_module
from plotting import save_plot_to_buffer

def analyze_interest_rate():
    try:
        # Use existing data fetcher
        df = dividend_module.get_dividend_data()
        
        if df.empty:
            return None, []

        # Focus on "Long Interest Rate"
        df_ir = df[['Long Interest Rate']].dropna()
        
        # Sort by Date
        df_ir = df_ir.sort_index()

        # Calculate Estimated Margin Rate (Low Cost Broker)
        MARGIN_SPREAD = 1.5
        df_ir['Margin Rate'] = df_ir['Long Interest Rate'] + MARGIN_SPREAD

        # Generate Plot
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df_ir.index, df_ir['Long Interest Rate'], label='Long Interest Rate (10-Year Treasury)', color='#eab308')
        ax.plot(df_ir.index, df_ir['Margin Rate'], label=f'Est. Margin Rate (+{MARGIN_SPREAD}%)', color='#f43f5e', linestyle='--')
        
        ax.set_title('Historical Long Interest Rate vs Est. Margin Rate')
        ax.set_xlabel('Year')
        ax.set_ylabel('Rate (%)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        img = save_plot_to_buffer(fig)
        
        # Prepare Table Data (vectorized)
        df_ir_latest = df_ir.sort_index(ascending=False)
        
        table_data = []
        dates = df_ir_latest.index.strftime('%Y-%m')
        rates = df_ir_latest['Long Interest Rate'].values
        margin_rates = df_ir_latest['Margin Rate'].values
        
        for i in range(len(df_ir_latest)):
            table_data.append({
                'date': dates[i],
                'rate': f"{rates[i]:.2f}%",
                'margin_rate': f"{margin_rates[i]:.2f}%"
            })
            
        return img, table_data

    except Exception as e:
        print(f"Error in analyze_interest_rate: {e}")
        traceback.print_exc()
        return None, []
