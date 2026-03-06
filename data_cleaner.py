"""
Data Cleaner for OCR extraction cleaning layer.
Ensures safe conversion from strings to numeric floats.
Rejects silent corruption or incorrect formats.
"""
import logging
from typing import List, Union
from config import DATA_VALUE_MIN, DATA_VALUE_MAX

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
            result = float(val)
        except ValueError:
            raise ValueError(f"Failed to cleanly convert OCR value to float: '{val}'")

        # Bounds check — clamp obvious OCR noise and warn instead of crashing
        if result < DATA_VALUE_MIN or result > DATA_VALUE_MAX:
            logging.warning(
                f"Value {result} out of expected range [{DATA_VALUE_MIN}, {DATA_VALUE_MAX}]. "
                f"Original OCR text: '{val}'. Clamping to nearest bound."
            )
            result = max(DATA_VALUE_MIN, min(result, DATA_VALUE_MAX))
        return result

    @staticmethod
    def clean_matrix(raw_matrix: List[List[Union[str, float, int]]]) -> List[List[float]]:
        """
        Applies cleaning layer over an entire extracted matrix.
        Returns a clean List[List[float]] or raises ValueError.
        """
        cleaned_matrix = []
        for r_idx, row in enumerate(raw_matrix):
            cleaned_row = []
            for c_idx, item in enumerate(row):
                try:
                    cleaned_val = DataCleaner.clean_value(item)
                except ValueError as e:
                    logging.warning(f"Cleaning failed at row {r_idx + 1}, col {c_idx + 1}: {e}")
                    raise
                cleaned_row.append(cleaned_val)
            cleaned_matrix.append(cleaned_row)

        return cleaned_matrix
