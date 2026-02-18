
import dividend_module
import pandas as pd
import traceback

print("Checking dividend data...")
try:
    df = dividend_module.get_dividend_data()
    print(f"Data retrieved. Empty? {df.empty}")
    if not df.empty:
        print(f"Columns: {df.columns}")
        print(f"First row: {df.iloc[0]}")
        
    # Check if download is needed/working
    if df.empty:
        print("Data is empty. Attempting download...")
        dividend_module.download_shiller_data()
        df = dividend_module.get_dividend_data()
        print(f"Data retrieved after download. Empty? {df.empty}")
        
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
