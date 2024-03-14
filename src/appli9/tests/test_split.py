import unittest
import pandas as pd
from src.data.import_data import split_and_count

class TestSplitAndCount(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.data = {
            'names': ['John Doe', 'Jane Smith', 'Alice Johnson'],
            'ages': ['25', '30', '35']
        }
        self.df = pd.DataFrame(self.data)
    
    def test_split_names(self):
        """Test splitting names by space."""
        expected = pd.DataFrame({"names":  ['John Doe', 'Jane Smith', 'Alice Johnson']})
        result = split_and_count(self.df, 'names', ' ')
        pd.testing.assert_series_equal(result, expected['names'].str.split(" ").str.len())


if __name__ == '__main__':
    unittest.main()