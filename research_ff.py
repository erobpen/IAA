
import pandas_datareader.data as web
import datetime

def check_fama_french():
    try:
        # List of potentially relevant datasets
        datasets = [
            'F-F_Research_Data_Factors', # US returns
            'F-F_Research_Data_5_Factors_2x3',
            'Portfolios_Formed_on_BE-ME',
            'Portfolios_Formed_on_E-P',
            'Developed_5_Factors', # Global
            'Developed_Ex_US_5_Factors',
            'Global_5_Factors'
        ]

        print("Checking Fama-French Datasets...")
        
        for ds in datasets:
            try:
                # Try fetching '6_Portfolios_2x3' specifically to see if we get Small Value
                target_ds = '6_Portfolios_2x3'
                df = web.DataReader(target_ds, 'famafrench', start='2020-01-01')
                print(f"\nDataset: {target_ds}")
                if isinstance(df, dict):
                     for k, v in df.items():
                         print(f"    Key: {k}")
                         if hasattr(v, 'columns'):
                             print(f"    Columns: {v.columns.tolist()}")
                         try:
                             print(v.head(2))
                         except:
                             pass
                if isinstance(df, dict):
                     for k, v in df.items():
                         print(f"    Key: {k}, Type: {type(v)}")
                         # Print first few lines to see structure
                         try:
                             print(v.head(2))
                         except:
                             pass
            except Exception as e:
                print(f"  Error fetching {ds}: {e}")


    except Exception as e:
        print(f"General Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_fama_french()

