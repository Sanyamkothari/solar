"""
Hard Validation module for the factory QC pipeline.
Enforces strict structural requirements on incoming cleaned matrices.
Raises exceptions immediately on schema or constraint failures (No silent failures).
"""
import math
from typing import List
from config import TOTAL_POINTS, BUS_BARS, POINTS_PER_BAR

class ValidationError(Exception):
    """Custom exception raised for structural data validation errors."""
    pass

class Validator:
    @staticmethod
    def validate_matrix(matrix: List[List[float]]) -> None:
        """
        Applies strict structural validation.
        - Ensure exactly 16 rows.
        - Ensure exactly 7 columns per row.
        - Ensure total points exactly matches 112.
        """
        
        # 1. Row count validation
        if len(matrix) != BUS_BARS:
            row_count = len(matrix)
            raise ValidationError(
                f"Row structure mismatch: Expected {BUS_BARS} bus bars, got {row_count} rows."
            )

        # 2. Check inner elements constraints & Total points mapping
        total_points_extracted = 0
        for i, row in enumerate(matrix):
            if len(row) != POINTS_PER_BAR:
                raise ValidationError(
                    f"Column structure mismatch at row {i+1}: Expected {POINTS_PER_BAR} points, got {len(row)}."
                )
            
            # Since data_cleaner handles casting, this is a secondary sanity type check
            if not all(isinstance(val, (int, float)) for val in row):
                raise ValidationError(
                    f"Non-numeric values detected post-cleaning in row {i+1}. "
                    "All extracted points must be numeric (int or float)."
                )

            total_points_extracted += len(row)

            # Check for missing values (usually represented as None or NaN)
            if any(val is None or math.isnan(val) for val in row):
                 raise ValidationError(f"Missing (None/NaN) values detected in row {i+1}.")

        # 3. Hard Total Rule
        if total_points_extracted != TOTAL_POINTS:
            raise ValidationError(
                f"Hard Validation Failed: Extracted {total_points_extracted} points. "
                f"Strictly expected exactly {TOTAL_POINTS}."
            )

        # All structural rules passed
        return None
