
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import interest_rate

class TestMarginRate(unittest.TestCase):
    
    @patch('interest_rate.dividend_module')
    def test_analyze_interest_rate_margin(self, mock_div):
        # Mock Data
        dates = pd.date_range(start='2020-01-01', periods=3, freq='MS')
        df = pd.DataFrame(index=dates)
        # Long Rate: 2.0, 3.0, 4.0
        df['Long Interest Rate'] = [2.0, 3.0, 4.0]
        
        mock_div.get_dividend_data.return_value = df
        
        print("Running analyze_interest_rate with mock...")
        img, table = interest_rate.analyze_interest_rate()
        
        self.assertIsNotNone(img, "Image should not be None")
        self.assertEqual(len(table), 3, "Table should have 3 rows")
        
        # Verify Margin Rate calculation
        # Expected: 2.0+1.5=3.5, 3.0+1.5=4.5, 4.0+1.5=5.5
        
        # Table is sorted descending by date, so first row is 4.0 (last date)
        row0 = table[0]
        self.assertIn('margin_rate', row0)
        print(f"Row 0 Margin Rate: {row0['margin_rate']}")
        self.assertEqual(row0['margin_rate'], "5.50%")
        
        row1 = table[1]
        print(f"Row 1 Margin Rate: {row1['margin_rate']}")
        self.assertEqual(row1['margin_rate'], "4.50%")
        
        print("Margin Rate Logic Validated!")

if __name__ == '__main__':
    unittest.main()
