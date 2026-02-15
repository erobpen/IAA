import pandas_datareader.data as web
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import datetime
import database
import traceback

def analyze_inflation():
    try:
        print("Initializing database for Inflation...")
        database.init_db() # Ensures table exists
        
        # 1. Check what we have in DB
        last_date = database.get_latest_inflation_date()
        current_date = datetime.datetime.now()
        
        # 2. Determine fetch range
        # FRED updates monthly. 
        start_date = None
        
        if last_date:
            # Check if last_date is significantly in the past (e.g. > 40 days)
            # Inflation data is slow (monthly lag).
            days_diff = (current_date.date() - last_date).days
            if days_diff > 35:
                start_date = last_date + datetime.timedelta(days=1)
                print(f"Updating Inflation data from {start_date}...")
            else:
                print("Inflation data is up to date.")
        else:
            print("No Inflation data. Fetching full history...")
            start_date = datetime.datetime(1928, 1, 1)
            
        # 3. Fetch from FRED if needed
        if start_date:
            try:
                # CPIAUCNS: Consumer Price Index for All Urban Consumers: All Items in U.S. City Average
                new_data = web.DataReader('CPIAUCNS', 'fred', start_date, current_date)
                if not new_data.empty:
                    print(f"Downloaded {len(new_data)} new inflation records.")
                    database.save_inflation_data(new_data)
                else:
                    print("No new inflation data found on FRED.")
            except Exception as e:
                print(f"Error fetching from FRED: {e}")
                # Provide fallback/error handling if strictly needed, 
                # but for now we proceed with what we have in DB.

        # 4. Load ALL data from DB
        data = database.get_all_inflation_data()
        
        if data.empty:
            print("Warning: No inflation data available to analyze.")
            return None, []
            
        # 5. Analysis
        # Resample to Annual (Year End) for the table/chart as requested
        # 'YE' is modern pandas alias for Year End, 'A' is deprecated.
        annual_data = data.resample('YE').last()
        
        # Calculate Annual Inflation %
        annual_data['Inflation_Pct'] = annual_data['CPI'].pct_change() * 100
        
        # Calculate Cumulative Inflation (Growth of $1 since start)
        # Factor = CPI_current / CPI_start
        base_cpi = annual_data['CPI'].iloc[0]
        annual_data['Cumulative_Factor'] = annual_data['CPI'] / base_cpi
        
        # 6. Plotting
        print("Plotting Inflation...")
        plt.figure(figsize=(12, 6))
        plt.plot(annual_data.index, annual_data['Cumulative_Factor'], label='Cumulative Inflation (1928 Base)', linewidth=2, color='red')
        
        plt.title('Cumulative Inflation (Purchasing Power Decay Reverse)')
        plt.xlabel('Year')
        plt.ylabel('Growth of Price Level ($1 in 1928 becomes $X)')
        plt.grid(True, which="both", ls="-", alpha=0.2)
        plt.legend()
        
        output = io.BytesIO()
        plt.savefig(output, format='png')
        output.seek(0)
        plt.close()
        
        # 7. Prepare Table Data
        # Reset index
        annual_data = annual_data.reset_index()
        
        table_data = []
        initial_amount = 10000
        
        for _, row in annual_data.iterrows():
            inf_pct = row['Inflation_Pct']
            # First row has NaN inflation pct
            inf_str = f"{inf_pct:.2f}%" if pd.notna(inf_pct) else "-"
            
            cumulative = row['Cumulative_Factor']
            purchasing_power = initial_amount / cumulative
            
            table_data.append({
                'year': row['Date'].year,
                'inflation_pct': inf_str,
                'cumulative': f"{cumulative:.2f}x",
                'purchasing_power': f"${purchasing_power:,.0f}"
            })
            
        # Reverse to show newest first
        table_data.reverse()
        
        return output, table_data

    except Exception as e:
        print(f"Error in analyze_inflation: {e}")
        traceback.print_exc()
        return None, []
