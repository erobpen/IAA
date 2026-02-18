
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
        first_row = table[0]
        print(f"First row: {first_row}")
        
        if 'margin_rate' in first_row:
             print(f"Margin Rate found: {first_row['margin_rate']}")
        else:
             print("Margin Rate KEY MISSING!")
    else:
        print("Table generation failed.")
        
except Exception as e:
    print(f"Test Failed: {e}")
    import traceback
    traceback.print_exc()
