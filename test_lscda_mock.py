
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
import lscda

class TestLSCDA(unittest.TestCase):
    
    @patch('lscda.analyzer')
    @patch('lscda.small_cap')
    @patch('lscda.dividend_module')
    def test_analyze_lscda(self, mock_div, mock_small_cap, mock_analyzer):
        # 1. Mock Daily Data
        dates = pd.date_range(start='2023-01-01', end='2023-01-10', freq='D')
        daily_df = pd.DataFrame(index=dates)
        daily_df['Close'] = 100.0
        daily_df['Regime'] = [1]*5 + [0]*5 # 5 days Bull, 5 days Bear
        daily_df['Simple_Ref'] = 0.01 # 1% Price Return
        daily_df['Total_Return_Daily'] = 0.01
        daily_df['Strategy_3x_Daily'] = np.where(daily_df['Regime'] == 1, 0.03, 0.0)
        daily_df['LSC_Growth'] = (1 + daily_df['Strategy_3x_Daily']).cumprod() * 10000 # Dummy
        
        mock_analyzer.get_strategy_data.return_value = daily_df
        
        # 2. Mock Small Cap Data
        sc_dates = pd.date_range(start='2023-01-01', periods=1, freq='MS')
        sc_df = pd.DataFrame(index=sc_dates)
        sc_df['Small_Value_Ret'] = 0.05
        mock_small_cap.get_small_cap_data.return_value = sc_df
        
        # 3. Mock Dividend Data
        div_df = pd.DataFrame(index=sc_dates)
        div_df['Dividend Yield'] = 2.0 # 2% Annual Yield
        mock_div.get_dividend_data.return_value = div_df
        
        # 4. Run verify
        print("Running analyze_lscda with mocks...")
        img, table = lscda.analyze_lscda()
        
        self.assertIsNotNone(img)
        self.assertTrue(len(table) > 0)
        
        # Check values
        # Regime 1: Should be 3 * (PriceRet + DailyDiv)
        # PriceRet = 0.01
        # DailyDiv approx 2%/252 approx 0.000079
        # Total = 0.010079
        # 3x = 0.03023
        
        # LSC (Regime 1) used just 3x PriceRet = 0.03
        
        # Check difference
        # We need to find a row with Regime 1
        r1 = [r for r in table if r['regime'] == 1][0]
        print(f"Regime 1 Row: {r1}")
        
if __name__ == '__main__':
    unittest.main()
