import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, Depends
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Adjust Python path
import sys
BASE_DIR = Path(__file__).parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import (
    INPUT_DIR, PROCESSED_DIR, FAILED_DIR, OUTPUT_DIR, LOGS_DIR,
    RULE_A_THRESHOLD, RULE_B_THRESHOLD, RULE_C_THRESHOLD,
    MIN_POINTS_RULE_A, MAX_RULE_B_PER_BAR, MAX_RULE_C_TOTAL, MAX_RULE_C_PER_BAR,
    BUS_BARS, POINTS_PER_BAR, TOTAL_POINTS,
    RULE_A_PERCENTAGE, MIN_OCR_CONFIDENCE,
    DATA_VALUE_MIN, DATA_VALUE_MAX, MAX_FILE_SIZE_BYTES,
    VERIFY_TOLERANCE, VERIFY_MATCH_THRESHOLD
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

# Create static directory if it doesn't exist
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _file_info(f: Path) -> dict:
    """Build a JSON-safe dict for a file."""
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
    failed_count = len(list(FAILED_DIR.glob('*')))
    output_count = len(list(OUTPUT_DIR.glob('*')))
    pending_count = len(InputHandler.get_pending_files())

    return {
        "processed": processed_count,
        "failed": failed_count,
        "reports": output_count,
        "pending": pending_count,
    }


# ─────────────────────── File Listings ───────────────────────
@app.get("/api/processed")
async def list_processed():
    files = sorted(PROCESSED_DIR.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True)
    return {"files": [_file_info(f) for f in files if f.is_file()]}


@app.get("/api/failed")
async def list_failed():
    files = sorted(FAILED_DIR.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True)
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
    # Prevent path traversal
    if not filepath.resolve().is_relative_to(OUTPUT_DIR.resolve()):
        return JSONResponse(status_code=403, content={"error": "Forbidden"})
    return FileResponse(path=str(filepath), filename=filename)


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
@app.get("/api/config")
async def get_config():
    return {
        "structure": {
            "bus_bars": BUS_BARS,
            "points_per_bar": POINTS_PER_BAR,
            "total_points": TOTAL_POINTS,
        },
        "thresholds": {
            "rule_a_threshold": RULE_A_THRESHOLD,
            "rule_a_percentage": RULE_A_PERCENTAGE,
            "min_points_rule_a": MIN_POINTS_RULE_A,
            "rule_b_threshold": RULE_B_THRESHOLD,
            "max_rule_b_per_bar": MAX_RULE_B_PER_BAR,
            "rule_c_threshold": RULE_C_THRESHOLD,
            "max_rule_c_total": MAX_RULE_C_TOTAL,
            "max_rule_c_per_bar": MAX_RULE_C_PER_BAR,
        },
        "ocr": {
            "min_confidence": MIN_OCR_CONFIDENCE,
            "data_value_min": DATA_VALUE_MIN,
            "data_value_max": DATA_VALUE_MAX,
        },
        "verification": {
            "tolerance": VERIFY_TOLERANCE,
            "match_threshold": VERIFY_MATCH_THRESHOLD,
        },
        "system": {
            "max_file_size_mb": MAX_FILE_SIZE_BYTES / (1024 * 1024),
            "input_dir": str(INPUT_DIR),
            "processed_dir": str(PROCESSED_DIR),
            "failed_dir": str(FAILED_DIR),
            "output_dir": str(OUTPUT_DIR),
            "logs_dir": str(LOGS_DIR),
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_app:app", host="0.0.0.0", port=8000, reload=True)
