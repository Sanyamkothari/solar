"""
Data Cleaner for OCR extraction cleaning layer.
Ensures safe conversion from strings to numeric floats.
Rejects silent corruption or incorrect formats.
"""
from typing import List, Union

class DataCleaner:
    @staticmethod
    def clean_value(val: Union[str, float, int]) -> float:
        """
        Safely converts common OCR mistakes to floats.
        Throws ValueError if conversion strictly fails.
        """
        if isinstance(val, (float, int)):
            return float(val)

        if not isinstance(val, str):
            raise ValueError(f"Unexpected type for cleaning: {type(val)} - Value: {val}")

        val = val.strip()

        # Handle exact common OCR substitutions
        # O to 0
        val = val.replace("O", "0").replace("o", "0")
        
        # Commas to periods (0,85 -> 0.85)
        val = val.replace(",", ".")
        
        # Try direct float conversion
        try:
            return float(val)
        except ValueError:
            raise ValueError(f"Failed to cleanly convert OCR value to float: '{val}'")

    @staticmethod
    def clean_matrix(raw_matrix: List[List[Union[str, float, int]]]) -> List[List[float]]:
        """
        Applies cleaning layer over an entire extracted matrix.
        Returns a clean List[List[float]] or raises ValueError.
        """
        cleaned_matrix = []
        for row in raw_matrix:
            cleaned_row = []
            for item in row:
                cleaned_val = DataCleaner.clean_value(item)
                cleaned_row.append(cleaned_val)
            cleaned_matrix.append(cleaned_row)
            
        return cleaned_matrix
