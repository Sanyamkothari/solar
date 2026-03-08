"""
Hard Validation module for the factory QC pipeline.
Enforces strict structural requirements on incoming cleaned matrices.
Raises exceptions immediately on schema or constraint failures (No silent failures).
"""
import math
import logging
from typing import List, Optional
from config import TOTAL_POINTS, BUS_BARS, POINTS_PER_BAR, MIN_BUS_BARS

class ValidationError(Exception):
    """Custom exception raised for structural data validation errors."""
    pass

class ValidationWarning:
    """Returned (not raised) when the matrix is structurally usable but not ideal."""
    def __init__(self, message: str):
        self.message = message
    def __str__(self):
        return self.message

class Validator:
    @staticmethod
    def validate_matrix(matrix: List[List[float]]) -> Optional[ValidationWarning]:
        """
        Applies structural validation.
        - Full pass: exactly 16 rows × 7 columns (112 points).
        - Partial pass: >= MIN_BUS_BARS rows × 7 columns — returns a ValidationWarning.
        - Hard fail: fewer than MIN_BUS_BARS rows, or column mismatches.
        """
        row_count = len(matrix)
        warning = None

        # 1. Row count validation
        if row_count < MIN_BUS_BARS:
            raise ValidationError(
                f"Row structure mismatch: Expected {BUS_BARS} bus bars, got {row_count} rows "
                f"(minimum {MIN_BUS_BARS} required)."
            )

        if row_count != BUS_BARS:
            warning = ValidationWarning(
                f"Partial matrix: got {row_count}/{BUS_BARS} bus bars. "
                f"QC rules will be applied proportionally."
            )
            logging.warning(warning.message)

        # 2. Check inner element constraints
        total_points_extracted = 0
        for i, row in enumerate(matrix):
            if len(row) != POINTS_PER_BAR:
                raise ValidationError(
                    f"Column structure mismatch at row {i+1}: Expected {POINTS_PER_BAR} points, got {len(row)}."
                )
            
            if not all(isinstance(val, (int, float)) for val in row):
                raise ValidationError(
                    f"Non-numeric values detected post-cleaning in row {i+1}. "
                    "All extracted points must be numeric (int or float)."
                )

            total_points_extracted += len(row)

            if any(val is None or math.isnan(val) for val in row):
                 raise ValidationError(f"Missing (None/NaN) values detected in row {i+1}.")

        # 3. Total points check (proportional for partial matrices)
        expected_total = row_count * POINTS_PER_BAR
        if total_points_extracted != expected_total:
            raise ValidationError(
                f"Hard Validation Failed: Extracted {total_points_extracted} points. "
                f"Expected exactly {expected_total} ({row_count} rows × {POINTS_PER_BAR} cols)."
            )

        return warning
