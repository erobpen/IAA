
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import io
import datetime
import requests
import zipfile

# Use Agg backend
matplotlib.use('Agg')

def get_small_cap_data():
    """
    Fetches Fama-French Small Cap Value data manually from the website.
    Bypasses pandas_datareader and read_csv issues by manually parsing lines.
    """
    try:
        # URL for 6 Portfolios Formed on Size and Book-to-Market (2 x 3)
        # CSV format
        url = "http://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/6_Portfolios_2x3_CSV.zip"
        
        print(f"Downloading from {url}...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            print(f"Failed to download data: {r.status_code}")
            return pd.DataFrame()
            
        z = zipfile.ZipFile(io.BytesIO(r.content))
        filename = z.namelist()[0]
        print(f"Extracting {filename}...")
        
        with z.open(filename) as f:
             lines = f.readlines()
             
        # Decoding
        decoded_lines = []
        for line in lines:
            try:
                decoded_lines.append(line.decode('utf-8').strip())
            except:
                continue
                
        # 1. Find Header
        header_index = -1
        # Look for header. Usually the first line with "SMALL LoBM"
        for i, line in enumerate(decoded_lines[:100]):
            if "SMALL LoBM" in line or "Small LoBM" in line:
                header_index = i
                break
        
        if header_index == -1:
            print("DEBUG: Header not found.")
            return pd.DataFrame()
            
        # Parse Header Columns
        # Split by comma or whitespace
        header_line = decoded_lines[header_index]
        if ',' in header_line:
            columns = [c.strip() for c in header_line.split(',')]
        else:
            columns = header_line.split()
            
        print(f"DEBUG: Columns detected: {columns}")
        
        # 2. Iterate Data Rows
        dates = []
        values = []
        
        # We need to find which column index corresponds to Small Value
        # Target: Small Value (SMALL HiBM)
        target_idx = -1
        for idx, col in enumerate(columns):
            if "SMALL HiBM" in col or "Small HiBM" in col:
                target_idx = idx
                break
                
        # Fallback if name not found but structure is standard 6 portfolios
        if target_idx == -1 and len(columns) >= 6:
             # 0=Small Lo, 1=Small Med, 2=Small Hi
             target_idx = 2
             print("DEBUG: Using index 2 for Small Value fallback.")
        
        if target_idx == -1:
             print("DEBUG: Could not identifying Small Value column.")
             return pd.DataFrame()

        # Iterate rows
        for i in range(header_index + 1, len(decoded_lines)):
            line = decoded_lines[i]
            if not line:
                continue
                
            # Split line
            if ',' in line:
                parts = [p.strip() for p in line.split(',')]
            else:
                parts = line.split()
                
            if not parts:
                continue
                
            date_str = parts[0]
            # Check if valid monthly date (6 digits)
            if len(date_str) == 6 and date_str.isdigit():
                # We expect date + 6 values = 7 parts (if date column is not in header)
                # Or date + N values.
                
                # Check target index
                # If parts[0] is date, then value is at target_idx + offset
                # If header included "Date" or "Unnamed", then target_idx matches.
                # If header did NOT include Date, then parts has 1 extra item at start.
                
                val_idx = target_idx
                if len(parts) == len(columns) + 1:
                    val_idx = target_idx + 1 # Shift because date is extra
                    
                if val_idx < len(parts):
                    val_str = parts[val_idx]
                    
                    # Check for date reset (New Block detection)
                    if dates:
                        last_date = dates[-1]
                        if date_str <= last_date:
                            print(f"DEBUG: Date reset detected ({last_date} -> {date_str}). Stopping.")
                            break

                    dates.append(date_str)
                    values.append(val_str)
            
            # Stop if we hit Annual block (Optional optimization)
            # If date is 4 digits, it's annual
            if len(date_str) == 4 and date_str.isdigit():
                 # We are likely in annual block
                 pass

        if not dates:
            print("DEBUG: No data rows parsing.")
            return pd.DataFrame()
            
        df = pd.DataFrame({'Date': dates, 'Small_Value_Ret': values})
        
        # Convert types
        df['Date'] = pd.to_datetime(df['Date'], format='%Y%m')
        df.set_index('Date', inplace=True)
        df['Small_Value_Ret'] = pd.to_numeric(df['Small_Value_Ret'], errors='coerce') / 100.0
        
        # Add Year
        df['Year'] = df.index.year
        
        print(f"DEBUG: Successfully parsed {len(df)} rows.")
        return df

    except Exception as e:
        print(f"Error getting small cap data manually: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def analyze_small_cap():
    try:
        # 1. Fetch Data
        df = get_small_cap_data()
        
        if df.empty:
            return None, [], "N/A"
            
        # 2. Monthly Data Processing (No Annual Resampling)
        # Calculate Index (Base 100)
        df['Growth_Index'] = (1 + df['Small_Value_Ret']).cumprod() * 100.0
        
        # We want to show monthly data: Date, Yield (%), Index Value
        
        # 3. Plotting (Optional based on user request "maybe if possible some index")
        # Let's plot the Index Value (base 100) on semilog
        plt.figure(figsize=(10, 6))
        plt.semilogy(df.index, df['Growth_Index'], label='Small Cap Value Index (Base 100)', color='#d946ef', linewidth=1.5)
        
        plt.title('Small Cap Value Index (1926=100)')
        plt.ylabel('Index Value (Log Scale)')
        plt.xlabel('Year')
        plt.grid(True, which="both", ls="-", alpha=0.2)
        plt.legend()
        
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        plt.close()
        
        # 4. Table Data (Monthly)
        # Sort desc by Date
        # Since it's monthly, we have 1000+ rows. The frontend might need to handle this or just show it.
        # Format Date as YYYY-MM
        table_records = df.sort_index(ascending=False)
        
        table_data = []
        for date_idx, row in table_records.iterrows():
            ret_val = row['Small_Value_Ret']
            ret_str = f"{ret_val*100:.2f}%" if pd.notna(ret_val) else "-"
            
            table_data.append({
                'date': date_idx.strftime('%Y-%m'),
                'yield': ret_str,
                'index_value': f"{row['Growth_Index']:,.2f}"
            })
            
        
        # Calculate CAGR (Compound Annual Growth Rate)
        # Formula: (End_Value / Start_Value) ^ (12 / Total_Months) - 1
        # Start Value is 100.0
        if not df.empty:
             end_val = df['Growth_Index'].iloc[-1]
             months = len(df)
             cagr = (end_val / 100.0) ** (12 / months) - 1
             cagr_str = f"{cagr*100:.2f}%"
        else:
             cagr_str = "N/A"

        return img, table_data, cagr_str

    except Exception as e:
        print(f"Error in analyze_small_cap: {e}")
        import traceback
        traceback.print_exc()
        return None, [], "Error"

if __name__ == "__main__":
    analyze_small_cap()
