
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import interest_rate

class TestInterestRate(unittest.TestCase):
    
    @patch('interest_rate.dividend_module')
    def test_analyze_interest_rate(self, mock_div):
        # Mock Data
        dates = pd.date_range(start='2020-01-01', periods=5, freq='MS')
        df = pd.DataFrame(index=dates)
        df['Long Interest Rate'] = [1.5, 1.6, 1.5, 1.4, 1.5]
        
        mock_div.get_dividend_data.return_value = df
        
        print("Running analyze_interest_rate with mock...")
        img, table = interest_rate.analyze_interest_rate()
        
        self.assertIsNotNone(img, "Image should not be None")
        self.assertEqual(len(table), 5, "Table should have 5 rows")
        
        print("Test Passed!")

if __name__ == '__main__':
    unittest.main()
