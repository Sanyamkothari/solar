"""
Cross-Verification module for the QC Automation pipeline.
Compares the OCR-extracted matrix (from image) against the user-provided Excel matrix
to detect discrepancies before applying quality rules.
"""
from typing import List, Dict, Tuple
from config import VERIFY_TOLERANCE, VERIFY_MATCH_THRESHOLD, BUS_BARS, POINTS_PER_BAR


class CrossVerifier:
    @staticmethod
    def verify(image_matrix: List[List[float]], excel_matrix: List[List[float]]) -> Dict:
        """
        Cell-by-cell comparison of the OCR-extracted matrix vs the Excel reference matrix.
        Returns a detailed verification report.
        """
        mismatches = []
        total_cells = 0
        matched_cells = 0

        rows_img = len(image_matrix)
        rows_xl = len(excel_matrix)
        rows_to_check = min(rows_img, rows_xl, BUS_BARS)

        for r in range(rows_to_check):
            cols_img = len(image_matrix[r])
            cols_xl = len(excel_matrix[r])
            cols_to_check = min(cols_img, cols_xl, POINTS_PER_BAR)

            for c in range(cols_to_check):
                total_cells += 1
                img_val = image_matrix[r][c]
                xl_val = excel_matrix[r][c]
                diff = abs(img_val - xl_val)

                if diff <= VERIFY_TOLERANCE:
                    matched_cells += 1
                else:
                    mismatches.append({
                        "bar": r + 1,
                        "point": c + 1,
                        "image_value": img_val,
                        "excel_value": xl_val,
                        "difference": round(diff, 4),
                    })

        match_ratio = matched_cells / total_cells if total_cells > 0 else 0.0
        passed = match_ratio >= VERIFY_MATCH_THRESHOLD

        # Build per-bar mismatch summary
        bar_mismatch_counts = {}
        for m in mismatches:
            bar_mismatch_counts[m["bar"]] = bar_mismatch_counts.get(m["bar"], 0) + 1

        return {
            "passed": passed,
            "total_cells": total_cells,
            "matched_cells": matched_cells,
            "mismatch_count": len(mismatches),
            "match_percentage": round(match_ratio * 100, 2),
            "tolerance": VERIFY_TOLERANCE,
            "mismatches": mismatches,
            "bar_mismatch_counts": bar_mismatch_counts,
        }

    @staticmethod
    def choose_matrix(verification_report: Dict,
                      image_matrix: List[List[float]],
                      excel_matrix: List[List[float]]) -> Tuple[List[List[float]], str]:
        """
        Conditional logic: decides which matrix to trust based on verification results.
        Returns (chosen_matrix, source_label).

        Rules:
        - If verification PASSED (>= 95% match): use excel_matrix (ground truth).
        - If verification FAILED (< 95% match): use excel_matrix (more reliable than OCR)
          but flag the batch for manual review.
        """
        if verification_report["passed"]:
            return excel_matrix, "EXCEL (verified — OCR matches)"
        else:
            return excel_matrix, "EXCEL (OCR mismatch detected — using Excel as ground truth)"
