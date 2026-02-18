
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import traceback
import dividend_module

def analyze_interest_rate():
    try:
        # Use existing data fetcher
        # Returns DF with columns: Date, SP500, Dividend, Earnings, CPI, Long Interest Rate, etc.
        df = dividend_module.get_dividend_data()
        
        if df.empty:
            return None, []

        # Focus on "Long Interest Rate"
        # Filter for validity (drop NaN)
        df_ir = df[['Long Interest Rate']].dropna()
        
        # Sort by Date
        df_ir = df_ir.sort_index()

        # Generate Plot
        plt.figure(figsize=(10, 6))
        plt.plot(df_ir.index, df_ir['Long Interest Rate'], label='Long Interest Rate (10-Year Treasury)', color='#eab308') # Yellow/Gold
        
        plt.title('Historical Long Interest Rate (Annual %)')
        plt.xlabel('Year')
        plt.ylabel('Rate (%)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Save plot
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        plt.close()
        
        # Prepare Table Data
        # Sort descending by date
        df_ir_latest = df_ir.sort_index(ascending=False)
        
        table_data = []
        for date, row in df_ir_latest.iterrows():
            table_data.append({
                'date': date.strftime('%Y-%m'),
                'rate': f"{row['Long Interest Rate']:.2f}%"
            })
            
        return img, table_data

    except Exception as e:
        print(f"Error in analyze_interest_rate: {e}")
        traceback.print_exc()
        return None, []
