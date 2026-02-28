"""
Report Generator for the factory QC pipeline.
Outputs a standardized Excel report with highlighting for ease of operator reading.
Saves to the `/output` folder with the Batch ID.
"""
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
from typing import List, Dict
from pathlib import Path
from config import (
    OUTPUT_DIR,
    RULE_A_THRESHOLD,
    RULE_B_THRESHOLD,
    RULE_C_THRESHOLD
)
from logger import logger

# Colors
RED_FILL = PatternFill(start_color="FF9999", end_color="FF9999", fill_type="solid")
GREEN_FILL = PatternFill(start_color="99FF99", end_color="99FF99", fill_type="solid")
YELLOW_FILL = PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid")

class ReportGenerator:
    @staticmethod
    def generate_report(batch_id: str, matrix: List[List[float]], eval_report: Dict) -> Path:
        """
        Generates the final Excel file.
        Includes two sheets:
        1. Cleaned Data (with color highlights for failures).
        2. QC Summary (Pass/Fail metrics).
        """
        wb = openpyxl.Workbook()
        
        # Sheet 1: Data Viewer
        ws_data = wb.active
        ws_data.title = "Cleaned Data"
        
        # Write Title & Decision
        ws_data["A1"] = f"Batch ID: {batch_id}"
        ws_data["A2"] = "Decision:"
        ws_data["B2"] = eval_report["decision"]
        
        # Color decision box
        if eval_report["decision"] == "APPROVED":
            ws_data["B2"].fill = GREEN_FILL
        elif eval_report["decision"] == "REJECTED":
            ws_data["B2"].fill = RED_FILL
        else:
            ws_data["B2"].fill = YELLOW_FILL
            
        ws_data["B2"].font = Font(bold=True)
        
        # Write Matrix with Rule Highlights
        start_row = 5
        ws_data.cell(row=start_row, column=1, value="s/n").font = Font(bold=True)
        for i in range(7):
            ws_data.cell(row=start_row, column=i+2, value=f"P{i+1}").font = Font(bold=True)
            
        for r_idx, row in enumerate(matrix, start=start_row+1):
            ws_data.cell(row=r_idx, column=1, value=f"Bus Bar {r_idx - start_row}")
            for c_idx, val in enumerate(row, start=2):
                cell = ws_data.cell(row=r_idx, column=c_idx, value=val)
                
                # Highlight failures
                if val <= RULE_C_THRESHOLD:
                    cell.fill = PatternFill(start_color="FF6666", end_color="FF6666", fill_type="solid") # Darker red for severe fail
                elif val <= RULE_B_THRESHOLD:
                    cell.fill = RED_FILL
                elif val > RULE_A_THRESHOLD:
                    cell.fill = GREEN_FILL
        
        # Sheet 2: Metrics Summary
        ws_summary = wb.create_sheet(title="QC Summary")
        
        # Extract metrics
        metrics = eval_report.get("metrics", {})
        rule_a = metrics.get("rule_A", {})
        rule_b = metrics.get("rule_B", {})
        rule_c = metrics.get("rule_C", {})
        
        rows = [
            ["Metric", "Value", "Threshold/Rule", "Passed"],
            ["Rule A: >0.8 Points", rule_a.get("points_gt_08"), f">= {rule_a.get('required')}", str(rule_a.get("passed"))],
            ["Rule B: Max <=0.35 per bar", "See Data Sheet", "<= 2 per bar", str(rule_b.get("passed"))],
            ["Rule C: Total <=0.1 Points", rule_c.get("total_failures"), "<= 8 Total", str(rule_c.get("passed"))],
            ["Rule C: Max <=0.1 per bar", "See Data Sheet", "<= 1 per bar", ""]
        ]
        
        for r_idx, row_data in enumerate(rows, start=1):
            for c_idx, val in enumerate(row_data, start=1):
                cell = ws_summary.cell(row=r_idx, column=c_idx, value=val)
                if r_idx == 1:
                    cell.font = Font(bold=True)
                
        # Save output
        out_path = OUTPUT_DIR / f"{batch_id}_Report.xlsx"
        wb.save(out_path)
        
        logger.info(f"Report generated successfully: {out_path.name}")
        return out_path
