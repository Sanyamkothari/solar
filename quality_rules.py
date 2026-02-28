"""
Quality Rules engine.
Applies Rule A, B, and C criteria on the validated matrices.
Determines final QC decision categories (APPROVED, REJECTED, etc.).
"""
from typing import List, Dict, Tuple
from config import (
    TOTAL_POINTS,
    BUS_BARS,
    RULE_A_THRESHOLD,
    MIN_POINTS_RULE_A,
    RULE_B_THRESHOLD,
    MAX_RULE_B_PER_BAR,
    RULE_C_THRESHOLD,
    MAX_RULE_C_TOTAL,
    MAX_RULE_C_PER_BAR,
    CATEGORY_APPROVED,
    CATEGORY_REJECTED
)

class QualityEvaluator:
    @staticmethod
    def evaluate_rule_a(matrix: List[List[float]]) -> Tuple[bool, int]:
        """
        Rule A: At least 75% of total points (84 points) must be > 0.8
        """
        total_greater_than_threshold = 0
        for current_idx, row in enumerate(matrix):
            total_greater_than_threshold += sum(1 for val in row if val > RULE_A_THRESHOLD)
            
        passed = total_greater_than_threshold >= MIN_POINTS_RULE_A
        return passed, total_greater_than_threshold

    @staticmethod
    def evaluate_rule_b(matrix: List[List[float]]) -> Tuple[bool, Dict[int, int]]:
        """
        Rule B: For each bus bar (7 points), maximum 2 points allowed <= 0.35.
        If any bus bar has more than 2, reject.
        """
        passed = True
        failures_per_bar = {}
        for bar_idx, row in enumerate(matrix):
            count_b = sum(1 for val in row if val <= RULE_B_THRESHOLD)
            failures_per_bar[bar_idx] = count_b
            if count_b > MAX_RULE_B_PER_BAR:
                passed = False
                
        return passed, failures_per_bar

    @staticmethod
    def evaluate_rule_c(matrix: List[List[float]]) -> Tuple[bool, int, Dict[int, int]]:
        """
        Rule C: Total points <= 0.1 allowed: maximum 8 AND Each bus bar can have maximum 1 point <= 0.1.
        """
        passed = True
        total_failures_c = 0
        failures_per_bar = {}
        
        for bar_idx, row in enumerate(matrix):
            count_c = sum(1 for val in row if val <= RULE_C_THRESHOLD)
            failures_per_bar[bar_idx] = count_c
            total_failures_c += count_c
            
            if count_c > MAX_RULE_C_PER_BAR:
                passed = False
                
        if total_failures_c > MAX_RULE_C_TOTAL:
            passed = False
            
        return passed, total_failures_c, failures_per_bar

    @staticmethod
    def evaluate_batch(matrix: List[List[float]]) -> Dict:
        """
        Evaluates the full batch against all rules.
        Returns a detailed report.
        """
        rule_a_pass, count_a = QualityEvaluator.evaluate_rule_a(matrix)
        rule_b_pass, dict_b = QualityEvaluator.evaluate_rule_b(matrix)
        rule_c_pass, total_c, dict_c = QualityEvaluator.evaluate_rule_c(matrix)
        
        overall_pass = rule_a_pass and rule_b_pass and rule_c_pass
        decision = CATEGORY_APPROVED if overall_pass else CATEGORY_REJECTED
        
        return {
            "decision": decision,
            "metrics": {
                "rule_A": {
                    "passed": rule_a_pass,
                    "points_gt_08": count_a,
                    "required": MIN_POINTS_RULE_A
                },
                "rule_B": {
                    "passed": rule_b_pass,
                    "failures_per_bar": dict_b, # dict map row_index: count
                },
                "rule_C": {
                    "passed": rule_c_pass,
                    "total_failures": total_c,
                    "failures_per_bar": dict_c # dict map row_index: count
                }
            }
        }
