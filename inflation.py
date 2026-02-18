import pandas_datareader.data as web
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import datetime
import traceback
import database
import data_cache
from plotting import save_plot_to_buffer

def analyze_inflation():
    try:
        print("Initializing Inflation analysis...")
        
        # 1. Check what we have in DB
        last_date = database.get_latest_inflation_date()
        current_date = datetime.datetime.now()
        
        # 2. Determine fetch range
        start_date = None
        
        if last_date:
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
                new_data = web.DataReader('CPIAUCNS', 'fred', start_date, current_date)
                if not new_data.empty:
                    print(f"Downloaded {len(new_data)} new inflation records.")
                    database.save_inflation_data(new_data)
                else:
                    print("No new inflation data found on FRED.")
            except Exception as e:
                print(f"Error fetching from FRED: {e}")

        # 4. Load ALL data from DB
        data = database.get_all_inflation_data()
        
        if data.empty:
            print("Warning: No inflation data available to analyze.")
            return None, [], "N/A", "N/A"
            
        # 5. Analysis
        annual_data = data.resample('YE').last()
        
        # Calculate Annual Inflation %
        annual_data['Inflation_Pct'] = annual_data['CPI'].pct_change() * 100
        
        # Calculate Cumulative Inflation (Growth of $1 since start)
        base_cpi = annual_data['CPI'].iloc[0]
        annual_data['Cumulative_Factor'] = annual_data['CPI'] / base_cpi
        
        # Calculate Average Annual Inflation (CAGR of CPI)
        if not annual_data.empty:
            start_cpi = annual_data['CPI'].iloc[0]
            end_cpi = annual_data['CPI'].iloc[-1]
            years = (annual_data.index[-1] - annual_data.index[0]).days / 365.25
            if years > 0:
                inf_cagr = (end_cpi / start_cpi) ** (1 / years) - 1
                inf_cagr_str = f"{inf_cagr*100:.2f}%"
            else:
                 inf_cagr_str = "N/A"
        else:
             inf_cagr_str = "N/A"
        
        # Calculate Average Annual Inflation Since 1942
        data_1942 = annual_data[annual_data.index.year >= 1942]
        
        if not data_1942.empty and len(data_1942) > 1:
            start_cpi_1942 = data_1942['CPI'].iloc[0]
            end_cpi_1942 = data_1942['CPI'].iloc[-1]
            years_1942 = (data_1942.index[-1] - data_1942.index[0]).days / 365.25
            
            if years_1942 > 0:
                inf_cagr_1942 = (end_cpi_1942 / start_cpi_1942) ** (1 / years_1942) - 1
                inf_cagr_1942_str = f"{inf_cagr_1942*100:.2f}%"
            else:
                 inf_cagr_1942_str = "N/A"
        else:
             inf_cagr_1942_str = "N/A"
        
        # 6. Plotting
        print("Plotting Inflation...")
        fig, ax1 = plt.subplots(figsize=(12, 6))
        
        # Primary Axis (Cumulative)
        color = 'tab:red'
        ax1.set_xlabel('Year')
        ax1.set_ylabel('Cumulative Inflation (Factor)', color=color)
        line1 = ax1.plot(annual_data.index, annual_data['Cumulative_Factor'], label='Cumulative Inflation', linewidth=2, color=color)
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.grid(True, which="both", ls="-", alpha=0.2)
        
        # Secondary Axis (Annual)
        ax2 = ax1.twinx()
        color = 'tab:blue'
        ax2.set_ylabel('Annual Inflation (%)', color=color)
        line2 = ax2.plot(annual_data.index, annual_data['Inflation_Pct'], label='Annual Inflation', linewidth=1, linestyle='--', color=color, alpha=0.6)
        ax2.tick_params(axis='y', labelcolor=color)
        
        # Combine legends
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc='upper left')
        
        plt.title('Inflation Analysis: Cumulative vs Annual')
        
        output = save_plot_to_buffer(fig)
        
        # 7. Prepare Table Data (vectorized)
        annual_reset = annual_data.reset_index()
        
        table_data = []
        initial_amount = 10000
        
        years_col = annual_reset['Date'].dt.year.values
        inf_pct_vals = annual_reset['Inflation_Pct'].values
        cumulative_vals = annual_reset['Cumulative_Factor'].values
        
        for i in range(len(annual_reset)):
            inf_pct = inf_pct_vals[i]
            inf_str = f"{inf_pct:.2f}%" if pd.notna(inf_pct) else "-"
            
            cumulative = cumulative_vals[i]
            purchasing_power = initial_amount / cumulative
            
            table_data.append({
                'year': int(years_col[i]),
                'inflation_pct': inf_str,
                'cumulative': f"{cumulative:.2f}x",
                'purchasing_power': f"${purchasing_power:,.0f}"
            })
            
        # Reverse to show newest first
        table_data.reverse()
        
        return output, table_data, inf_cagr_str, inf_cagr_1942_str
 
    except Exception as e:
        print(f"Error in analyze_inflation: {e}")
        traceback.print_exc()
        return None, [], "Error", "Error"

def calculate_period_cagr(start_year, end_year):
    """
    Calculates the CAGR of Inflation (CPI) between two years.
    Returns the percentage as a float (e.g., 3.5 for 3.5%).
    Returns None if data invalid.
    """
    try:
        # Load all data
        data = database.get_all_inflation_data()
        
        if data.empty:
            return None
            
        # Resample to Annual
        annual_data = data.resample('YE').last()
        
        try:
            start_row = annual_data.loc[annual_data.index.year == start_year]
            if start_row.empty:
                 return None
            start_cpi = start_row['CPI'].iloc[-1]
            
            end_row = annual_data.loc[annual_data.index.year == end_year]
            if end_row.empty:
                return None
            end_cpi = end_row['CPI'].iloc[-1]
            
            years = end_year - start_year
            
            if years <= 0:
                return 0.0
                
            cagr = (end_cpi / start_cpi) ** (1 / years) - 1
            return cagr * 100.0
            
        except IndexError:
            return None
            
    except Exception as e:
        print(f"Error in calculate_period_cagr: {e}")
        return None
