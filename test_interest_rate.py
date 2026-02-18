
import interest_rate
import pandas as pd

try:
    print("Testing analyze_interest_rate()...")
    img, table = interest_rate.analyze_interest_rate()
    
    if img:
        print("Image generated successfully.")
    else:
        print("Image generation failed.")
        
    if table:
        print(f"Table data generated with {len(table)} rows.")
        print(f"First row: {table[0]}")
    else:
        print("Table generation failed.")
        
except Exception as e:
    print(f"Test Failed: {e}")
    import traceback
    traceback.print_exc()
