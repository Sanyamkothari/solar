import os
import json
import shutil
import tempfile
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Adjust Python path
import sys
BASE_DIR = Path(__file__).parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

import config as cfg_module
from config import (
    INPUT_DIR, PROCESSED_DIR, FAILED_DIR, OUTPUT_DIR, LOGS_DIR,
)
from input_handler import InputHandler
from main import process_file

app = FastAPI(title="Factory QC Web Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _file_info(f: Path) -> dict:
    stat = f.stat()
    return {
        "name": f.name,
        "size": stat.st_size,
        "size_display": _human_size(stat.st_size),
        "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "extension": f.suffix.lower(),
    }

def _human_size(num_bytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


# ─────────────────────── Pages ───────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open(STATIC_DIR / "index.html", "r", encoding="utf-8") as f:
        return f.read()


# ─────────────────────── Metrics ───────────────────────
@app.get("/api/metrics")
async def get_metrics():
    processed_count = len(list(PROCESSED_DIR.glob('*')))
    output_count = len(list(OUTPUT_DIR.glob('*')))
    pending_count = len(InputHandler.get_pending_files())
    return {
        "processed": processed_count,
        "reports": output_count,
        "pending": pending_count,
    }


# ─────────────────────── File Listings ───────────────────────
@app.get("/api/processed")
async def list_processed():
    files = sorted(PROCESSED_DIR.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True)
    return {"files": [_file_info(f) for f in files if f.is_file()]}


@app.get("/api/reports")
async def list_reports():
    files = sorted(OUTPUT_DIR.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True)
    return {"files": [_file_info(f) for f in files if f.is_file()]}


@app.get("/api/reports/download/{filename}")
async def download_report(filename: str):
    filepath = OUTPUT_DIR / filename
    if not filepath.exists() or not filepath.is_file():
        return JSONResponse(status_code=404, content={"error": "File not found"})
    if not filepath.resolve().is_relative_to(OUTPUT_DIR.resolve()):
        return JSONResponse(status_code=403, content={"error": "Forbidden"})
    return FileResponse(path=str(filepath), filename=filename)


# ─────────────────────── Report Detail (for graphs) ───────────────────────
@app.get("/api/reports/detail/{filename}")
async def report_detail(filename: str):
    """Parse an Excel report and return structured data for graphing."""
    filepath = OUTPUT_DIR / filename
    if not filepath.exists() or not filepath.is_file():
        return JSONResponse(status_code=404, content={"error": "File not found"})
    if not filepath.resolve().is_relative_to(OUTPUT_DIR.resolve()):
        return JSONResponse(status_code=403, content={"error": "Forbidden"})

    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(filepath), data_only=True)

        # Extract data from "Cleaned Data" sheet
        ws = wb["Cleaned Data"]
        batch_id = str(ws["A1"].value or "")
        decision = str(ws["B2"].value or "UNKNOWN")

        # Read matrix (starts at row 6, col 2..8 for P1-P7, until no more data)
        matrix = []
        bar_labels = []
        row_idx = 6
        while True:
            label = ws.cell(row=row_idx, column=1).value
            if label is None:
                break
            bar_labels.append(str(label))
            row_vals = []
            for c in range(2, 9):
                v = ws.cell(row=row_idx, column=c).value
                row_vals.append(float(v) if v is not None else 0.0)
            matrix.append(row_vals)
            row_idx += 1

        # Extract QC Summary
        qc_summary = {}
        if "QC Summary" in wb.sheetnames:
            ws_qc = wb["QC Summary"]
            for r in range(2, 6):
                metric_name = ws_qc.cell(row=r, column=1).value
                metric_val = ws_qc.cell(row=r, column=2).value
                threshold = ws_qc.cell(row=r, column=3).value
                passed = ws_qc.cell(row=r, column=4).value
                if metric_name:
                    qc_summary[str(metric_name)] = {
                        "value": str(metric_val) if metric_val else "",
                        "threshold": str(threshold) if threshold else "",
                        "passed": str(passed) if passed else "",
                    }

        # Compute graph-ready stats
        all_values = [v for row in matrix for v in row if v >= 0]
        bar_averages = [sum(row) / max(len(row), 1) for row in matrix]
        point_averages = []
        if matrix:
            for col in range(len(matrix[0])):
                col_vals = [matrix[r][col] for r in range(len(matrix)) if matrix[r][col] >= 0]
                point_averages.append(sum(col_vals) / max(len(col_vals), 1))

        # Distribution bins
        bins = {"<0.1": 0, "0.1-0.35": 0, "0.35-0.8": 0, ">0.8": 0}
        for v in all_values:
            if v <= 0.1:
                bins["<0.1"] += 1
            elif v <= 0.35:
                bins["0.1-0.35"] += 1
            elif v <= 0.8:
                bins["0.35-0.8"] += 1
            else:
                bins[">0.8"] += 1

        return {
            "batch_id": batch_id,
            "decision": decision,
            "bar_labels": bar_labels,
            "matrix": matrix,
            "bar_averages": bar_averages,
            "point_averages": point_averages,
            "distribution": bins,
            "qc_summary": qc_summary,
            "stats": {
                "total_points": len(all_values),
                "mean": round(sum(all_values) / max(len(all_values), 1), 4),
                "min": round(min(all_values), 4) if all_values else 0,
                "max": round(max(all_values), 4) if all_values else 0,
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ─────────────────────── Upload & Process ───────────────────────
@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    excel_ref: Optional[UploadFile] = File(None)
):
    try:
        tmp_dir = Path(tempfile.mkdtemp(prefix="qc_upload_"))
        file_path = tmp_dir / file.filename

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        excel_ref_path = None
        if excel_ref and excel_ref.filename:
            excel_ref_path = tmp_dir / f"ref_{excel_ref.filename}"
            excel_content = await excel_ref.read()
            with open(excel_ref_path, "wb") as f:
                f.write(excel_content)

        result = process_file(file_path, excel_ref_path=excel_ref_path)
        return JSONResponse(status_code=200, content={"success": True, "data": result})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ─────────────────────── Logs ───────────────────────
@app.get("/api/logs")
async def get_logs():
    logs = list(LOGS_DIR.glob('*.log'))
    if logs:
        latest_log = max(logs, key=os.path.getctime)
        try:
            with open(latest_log, "r", encoding="utf-8") as f:
                lines = f.readlines()
            log_text = "".join(lines[-40:])
            return {"success": True, "source": latest_log.name, "logs": log_text}
        except Exception as e:
            return {"success": False, "error": str(e)}
    return {"success": True, "source": "None", "logs": "No logs generated yet. Process a file to begin."}


# ─────────────────────── Configuration ───────────────────────
# Editable config keys with their types
EDITABLE_CONFIG = {
    "structure": {
        "bus_bars": ("BUS_BARS", int),
        "points_per_bar": ("POINTS_PER_BAR", int),
    },
    "thresholds": {
        "rule_a_threshold": ("RULE_A_THRESHOLD", float),
        "rule_a_percentage": ("RULE_A_PERCENTAGE", float),
        "rule_b_threshold": ("RULE_B_THRESHOLD", float),
        "max_rule_b_per_bar": ("MAX_RULE_B_PER_BAR", int),
        "rule_c_threshold": ("RULE_C_THRESHOLD", float),
        "max_rule_c_total": ("MAX_RULE_C_TOTAL", int),
        "max_rule_c_per_bar": ("MAX_RULE_C_PER_BAR", int),
    },
    "ocr": {
        "min_confidence": ("MIN_OCR_CONFIDENCE", float),
        "data_value_min": ("DATA_VALUE_MIN", float),
        "data_value_max": ("DATA_VALUE_MAX", float),
    },
    "verification": {
        "tolerance": ("VERIFY_TOLERANCE", float),
        "match_threshold": ("VERIFY_MATCH_THRESHOLD", float),
    },
}

@app.get("/api/config")
async def get_config():
    return {
        "structure": {
            "bus_bars": cfg_module.BUS_BARS,
            "points_per_bar": cfg_module.POINTS_PER_BAR,
            "total_points": cfg_module.TOTAL_POINTS,
        },
        "thresholds": {
            "rule_a_threshold": cfg_module.RULE_A_THRESHOLD,
            "rule_a_percentage": cfg_module.RULE_A_PERCENTAGE,
            "min_points_rule_a": cfg_module.MIN_POINTS_RULE_A,
            "rule_b_threshold": cfg_module.RULE_B_THRESHOLD,
            "max_rule_b_per_bar": cfg_module.MAX_RULE_B_PER_BAR,
            "rule_c_threshold": cfg_module.RULE_C_THRESHOLD,
            "max_rule_c_total": cfg_module.MAX_RULE_C_TOTAL,
            "max_rule_c_per_bar": cfg_module.MAX_RULE_C_PER_BAR,
        },
        "ocr": {
            "min_confidence": cfg_module.MIN_OCR_CONFIDENCE,
            "data_value_min": cfg_module.DATA_VALUE_MIN,
            "data_value_max": cfg_module.DATA_VALUE_MAX,
        },
        "verification": {
            "tolerance": cfg_module.VERIFY_TOLERANCE,
            "match_threshold": cfg_module.VERIFY_MATCH_THRESHOLD,
        },
    }


@app.post("/api/config")
async def update_config(request: Request):
    """Update configuration values at runtime. Changes persist in memory only."""
    try:
        body = await request.json()
        updated = []
        for section, fields in body.items():
            if section not in EDITABLE_CONFIG:
                continue
            for key, value in fields.items():
                if key not in EDITABLE_CONFIG[section]:
                    continue
                attr_name, type_fn = EDITABLE_CONFIG[section][key]
                new_val = type_fn(value)
                setattr(cfg_module, attr_name, new_val)
                updated.append(f"{attr_name} = {new_val}")

        # Recompute derived values
        cfg_module.TOTAL_POINTS = cfg_module.BUS_BARS * cfg_module.POINTS_PER_BAR
        cfg_module.MIN_POINTS_RULE_A = int(cfg_module.TOTAL_POINTS * cfg_module.RULE_A_PERCENTAGE)

        return {"success": True, "updated": updated}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_app:app", host="0.0.0.0", port=8000, reload=True)
