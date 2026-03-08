"""
Test suite for the Manufacturing QC Automation Rules, Validation, and Cleaner.
Runs explicit boundary condition tests outlined in the spec.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from validator import Validator, ValidationError
from data_cleaner import DataCleaner
from quality_rules import QualityEvaluator

def get_base_matrix(val=1.0):
    """Utility to generate a 16x7 matrix filled with `val`."""
    return [[val for _ in range(7)] for _ in range(16)]

# --- DATA CLEANER TESTS ---
def test_cleaner_handles_ocr_mistakes():
    assert DataCleaner.clean_value("O.85") == 0.85
    assert DataCleaner.clean_value("o.85") == 0.85
    assert DataCleaner.clean_value("0,85") == 0.85
    assert DataCleaner.clean_value(" 0.90 ") == 0.90

def test_cleaner_raises_on_garbage():
    with pytest.raises(ValueError):
        DataCleaner.clean_value("X.XX")

# --- VALIDATOR TESTS ---
def test_validator_accepts_perfect_matrix():
    matrix = get_base_matrix()
    Validator.validate_matrix(matrix) # Should pass silently

def test_validator_rejects_wrong_rows():
    matrix = get_base_matrix()
    matrix.pop() # Remove one row -> 15 rows
    # 15 rows is still >= MIN_BUS_BARS, so it should return a warning (not raise)
    result = Validator.validate_matrix(matrix)
    assert result is not None  # Should be a ValidationWarning

def test_validator_rejects_wrong_cols():
    matrix = get_base_matrix()
    matrix[0].append(1.0) # Row 0 has 8 elements
    with pytest.raises(ValidationError, match="got 8"):
        Validator.validate_matrix(matrix)

def test_validator_rejects_missing_values():
    matrix = get_base_matrix()
    matrix[0][0] = None
    with pytest.raises(ValidationError, match="Non-numeric values"):
        Validator.validate_matrix(matrix)

# --- QUALITY RULE TESTS ---
def test_rule_a_exact_boundary():
    # Exactly 84 points > 0.8 -> Pass
    matrix = get_base_matrix(0.5) # All failing
    # Set exactly 84 to pass (12 rows * 7 = 84)
    for i in range(12):
        for j in range(7):
            matrix[i][j] = 0.9
            
    passed, count, required = QualityEvaluator.evaluate_rule_a(matrix)
    assert count == 84
    assert passed is True

    # 83 points -> Fail
    matrix[0][0] = 0.5 
    passed, count, required = QualityEvaluator.evaluate_rule_a(matrix)
    assert count == 83
    assert passed is False

def test_rule_b_exact_boundary():
    # Max 2 points <= 0.35 per bar -> Pass
    matrix = get_base_matrix(0.9)
    matrix[0][0] = 0.3 
    matrix[0][1] = 0.3 # 2 failures in row 0
    
    passed, dict_b = QualityEvaluator.evaluate_rule_b(matrix)
    assert passed is True
    assert dict_b[0] == 2

    # 3 points -> Fail
    matrix[0][2] = 0.3 
    passed, _ = QualityEvaluator.evaluate_rule_b(matrix)
    assert passed is False

def test_rule_c_exact_boundaries():
    # Total <= 8 allowed AND Max 1 per bar.
    matrix = get_base_matrix(0.9)
    
    # Give 8 different bars exactly 1 failure (<=0.1) -> Pass
    for i in range(8):
        matrix[i][0] = 0.05
    
    passed, total, per_bar = QualityEvaluator.evaluate_rule_c(matrix)
    assert passed is True
    assert total == 8

    # Give 9th bar a failure -> Total 9 -> Fail
    matrix[8][0] = 0.05
    passed, _, _ = QualityEvaluator.evaluate_rule_c(matrix)
    assert passed is False

    # Reset
    matrix = get_base_matrix(0.9)
    
    # Detail: Max 1 per bar. Let's give Bar 0 two failures -> Total is only 2, but per-bar fails -> Fail
    matrix[0][0] = 0.05
    matrix[0][1] = 0.05
    passed, total, _ = QualityEvaluator.evaluate_rule_c(matrix)
    assert passed is False
    assert total == 2
