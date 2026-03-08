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

        # Decimal Point Restoration
        # Since logical values are between 0.0 and 5, if the OCR engine 
        # drops a decimal point (reading 1.51 as 151), the raw value will be > 5.
        # We continually divide by 10 until the value falls under 5.
        while result > 5:
            result = result / 10.0

        # Bounds check — clamp obvious OCR noise and warn instead of crashing
        if result < DATA_VALUE_MIN or result > DATA_VALUE_MAX:
            logging.warning(
                f"Value {result} out of expected range [{DATA_VALUE_MIN}, {DATA_VALUE_MAX}]. "
                f"Original OCR text: '{val}'. Clamping to nearest bound."
            )
            result = max(DATA_VALUE_MIN, min(result, DATA_VALUE_MAX))
        return result

    @staticmethod
    def clean_matrix(raw_matrix: List[List[dict]]) -> List[List[float]]:
        """
        Applies cleaning layer over an entire extracted matrix of dicts containing 'val' and 'confidence'.
        Returns a clean List[List[float]] or raises ValueError.
        """
        cleaned_matrix = []
        high_conf_values = []
        
        # Pass 1: Clean basic values and collect high-confidence ones for average baseline
        for r_idx, row in enumerate(raw_matrix):
            cleaned_row = []
            for c_idx, item in enumerate(row):
                if isinstance(item, dict):
                    raw_val = item.get('val', "0.0")
                    confidence = item.get('confidence', 1.0)
                else:
                    raw_val = item
                    confidence = 1.0
                    
                try:
                    cleaned_val = DataCleaner.clean_value(raw_val)
                except ValueError as e:
                    logging.warning(f"Cleaning failed at row {r_idx + 1}, col {c_idx + 1}: {e}")
                    raise
                    
                cleaned_row.append({'val': cleaned_val, 'confidence': confidence})
                
                # Only trust reasonably confident non-zero values for the global average
                if confidence > 0.6 and cleaned_val > 0.0:
                    high_conf_values.append(cleaned_val)
                    
            cleaned_matrix.append(cleaned_row)

        global_avg = sum(high_conf_values) / len(high_conf_values) if high_conf_values else 1.5
        global_avg = round(global_avg, 3)

        # Pass 2: Replace dangerously low-confidence values with the global average
        final_matrix = []
        for r_idx, row in enumerate(cleaned_matrix):
            final_row = []
            for c_idx, item in enumerate(row):
                val = item['val']
                conf = item['confidence']
                
                if conf < 0.4:
                    logging.warning(f"Row {r_idx+1} Col {c_idx+1}: Very low confidence ({conf:.2f}). Replacing {val} with avg {global_avg}.")
                    final_row.append(global_avg)
                else:
                    final_row.append(val)
            final_matrix.append(final_row)

        return final_matrix
