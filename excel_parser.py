"""
Excel parser meant for processing raw Excel reports.
Returns the 16x7 numerical matrix for pipeline ingestion.
"""
from typing import List, Union
import openpyxl
from config import BUS_BARS, POINTS_PER_BAR
from data_cleaner import DataCleaner
from validator import ValidationError

class ExcelParser:
    @staticmethod
    def extract_matrix(filepath: str) -> List[List[float]]:
        """
        Extracts a matrix from the active Excel sheet.
        Assumes data is contiguous starting from some anchoring cell.
        By default, it will just search for the first 16x7 block of numbers.
        """
        try:
            wb = openpyxl.load_workbook(filepath, data_only=True)
            sheet = wb.active
        except Exception as e:
            raise ValidationError(f"Failed to load Excel file: {filepath}. Error: {e}")

        matrix: List[List[Union[str, float]]] = []
        
        # Simple extraction strategy: scan row by row, ignoring empty rows, 
        # picking up first exactly 7 element sequences until we find 16 of them.
        for row in sheet.iter_rows(values_only=True):
            # filter Nones and purely blank strings
            cleaned_row = [cell for cell in row if cell is not None and str(cell).strip() != ""]
            
            if len(cleaned_row) == POINTS_PER_BAR:
                matrix.append(cleaned_row)
            elif len(cleaned_row) > POINTS_PER_BAR:
                # If there are more, just take the first 7 assuming header cols on left
                # Adjust based on exact excel schema if needed.
                matrix.append(cleaned_row[:POINTS_PER_BAR])
                
            if len(matrix) == BUS_BARS:
                break
                
        if len(matrix) < BUS_BARS:
            raise ValidationError(
                f"Excel parsing failed. Expected {BUS_BARS} bus bars, but only found {len(matrix)} valid rows."
            )
            
        # Clean the matrix immediately upon extraction
        clean_matrix = DataCleaner.clean_matrix(matrix)
        
        return clean_matrix
