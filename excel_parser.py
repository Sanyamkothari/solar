"""
Excel parser meant for processing raw Excel reports.
Returns the 16x7 numerical matrix for pipeline ingestion.
Supports both .xlsx (openpyxl) and .xls (xlrd) file formats.
"""
from typing import List, Union, Optional, Tuple
import openpyxl
import logging

from config import BUS_BARS, POINTS_PER_BAR
from data_cleaner import DataCleaner
from validator import ValidationError

# Summary row labels to skip (case-insensitive check)
_SUMMARY_LABELS = {"maximum", "minimum", "mean", "average", "total", "result", "max", "min"}


class ExcelParser:

    @staticmethod
    def _load_rows(filepath: str) -> List[List]:
        """Load all rows from an Excel file (.xlsx or .xls) as lists of cell values."""
        ext = filepath.rsplit(".", 1)[-1].lower()

        if ext == "xlsx":
            try:
                wb = openpyxl.load_workbook(filepath, data_only=True)
                sheet = wb.active
                return [list(row) for row in sheet.iter_rows(values_only=True)]
            except Exception as e:
                raise ValidationError(f"Failed to load .xlsx file: {filepath}. Error: {e}")

        elif ext == "xls":
            try:
                import xlrd
            except ImportError:
                raise ValidationError(
                    "xlrd library is required to read .xls files. Install it with: pip install xlrd"
                )
            try:
                wb = xlrd.open_workbook(filepath)
                sheet = wb.sheet_by_index(0)
                rows = []
                for r in range(sheet.nrows):
                    rows.append([sheet.cell_value(r, c) for c in range(sheet.ncols)])
                return rows
            except Exception as e:
                raise ValidationError(f"Failed to load .xls file: {filepath}. Error: {e}")

        else:
            raise ValidationError(f"Unsupported Excel format: .{ext}")

    @staticmethod
    def _find_header_row(rows: List[List]) -> Optional[int]:
        """
        Locate the data-table header row by looking for cells containing
        keywords like 'force' or 'interval' (case-insensitive).
        Returns the row index, or None if not found.
        """
        for idx, row in enumerate(rows):
            force_hits = 0
            for cell in row:
                if cell is not None and isinstance(cell, str):
                    low = cell.lower()
                    if "force" in low or "interval" in low:
                        force_hits += 1
            if force_hits >= 3:
                return idx
        return None

    @staticmethod
    def _detect_force_columns(header_row: List) -> List[int]:
        """
        Given the header row, return the column indices that correspond to the
        7 interval force measurements (skip 'No.' and 'max avg' columns).
        """
        force_cols: List[int] = []
        for col_idx, cell in enumerate(header_row):
            if cell is None or not isinstance(cell, str):
                continue
            low = cell.lower()
            # Match columns like "MaxForce @ 1st interval", "Force @ 2nd interval" etc.
            if ("force" in low and "interval" in low) and "avg" not in low:
                force_cols.append(col_idx)
        return force_cols[:POINTS_PER_BAR]  # at most 7

    @staticmethod
    def _is_numeric(val) -> bool:
        """Check if a value can be interpreted as a number."""
        if isinstance(val, (int, float)):
            return True
        if isinstance(val, str):
            v = val.strip().replace(",", ".").replace("O", "0").replace("o", "0")
            try:
                float(v)
                return True
            except ValueError:
                return False
        return False

    @staticmethod
    def _row_is_summary(row: List, force_cols: List[int]) -> bool:
        """Return True if this row is a summary row (Maximum, Minimum, Mean, etc.)."""
        for cell in row:
            if isinstance(cell, str) and cell.strip().lower() in _SUMMARY_LABELS:
                return True
        return False

    @staticmethod
    def _extract_numeric_values(row: List, force_cols: Optional[List[int]]) -> List:
        """
        Extract force values from a row.
        If force_cols are known, use those specific columns.
        Otherwise, fall back to extracting all numeric values from the row.
        """
        if force_cols:
            vals = []
            for ci in force_cols:
                if ci < len(row):
                    vals.append(row[ci])
            return vals

        # Fallback: collect only numeric values
        return [cell for cell in row if cell is not None and ExcelParser._is_numeric(cell)]

    @staticmethod
    def extract_matrix(filepath: str) -> List[List[float]]:
        """
        Extracts the 16×7 force matrix from an Excel peel test report.
        Anchors to the data table header row, identifies force columns,
        then reads the 16 data rows below (skipping summary rows).
        """
        rows = ExcelParser._load_rows(filepath)

        header_idx = ExcelParser._find_header_row(rows)
        force_cols: Optional[List[int]] = None

        if header_idx is not None:
            force_cols = ExcelParser._detect_force_columns(rows[header_idx])
            if len(force_cols) < POINTS_PER_BAR:
                logging.warning(
                    f"Header detected at row {header_idx} but only {len(force_cols)} "
                    f"force columns found (expected {POINTS_PER_BAR}). Falling back to numeric scan."
                )
                force_cols = None
            start_row = header_idx + 1
        else:
            logging.warning("Could not locate data-table header. Falling back to numeric scan.")
            start_row = 0

        matrix: List[List] = []

        for row in rows[start_row:]:
            # Skip summary rows
            if ExcelParser._row_is_summary(row, force_cols):
                continue

            vals = ExcelParser._extract_numeric_values(row, force_cols)

            if len(vals) == POINTS_PER_BAR:
                matrix.append(vals)
            elif len(vals) > POINTS_PER_BAR and force_cols is None:
                # Fallback mode — take first 7 numeric values
                matrix.append(vals[:POINTS_PER_BAR])

            if len(matrix) == BUS_BARS:
                break

        if len(matrix) < BUS_BARS:
            raise ValidationError(
                f"Excel parsing failed. Expected {BUS_BARS} bus bars, but only found {len(matrix)} valid rows."
            )

        # Clean the matrix immediately upon extraction
        clean_matrix = DataCleaner.clean_matrix(matrix)

        return clean_matrix
