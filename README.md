# Solar QC — Automated Solder Point Inspection System

An end-to-end quality control pipeline for manufacturing solder point inspection.
The system uses Google Cloud Vision OCR and classical image processing to extract
measurement data from factory test equipment photos, applies configurable QC rules,
and generates detailed Excel inspection reports.

---

## Overview

The system accepts two types of input:

- **Images** (PNG / JPG / JPEG) — photographs of factory monitor screens showing solder force data
- **Excel files** (XLSX / XLS) — direct spreadsheet exports of measurement data

It processes each file through a structured pipeline, evaluates the extracted data against
QC rules, and produces a structured decision with a downloadable Excel report.

---

## Pipeline Architecture

### 1) Image Preprocessing (`image_processor.py`)

When an image is uploaded, the following steps are applied before OCR:

- **Crop** — configurable margins to remove UI chrome around the data table
- **Deskew** — corrects rotation from handheld photography
- **Perspective correction** — flattens slightly angled shots
- **Contrast enhancement** — CLAHE adaptive histogram equalisation
- **Denoising** — mild Gaussian smoothing to reduce compression artifacts
- **Sharpening** — unsharp mask to improve character edge clarity

### 2) OCR and Matrix Reconstruction (`ocr_engine.py`)

The preprocessed image is sent to the **Google Cloud Vision** document text detection API.

The response is then processed as follows:

- All text annotations are scanned to locate table boundary keywords (`interval`, `force`, `1st`, `2nd`, `maximum`, `minimum`, `mean`)
- Numeric tokens within the table boundary are extracted with their pixel coordinates and confidence scores
- Tokens are grouped into rows using an adaptive Y-coordinate threshold
- Oversized lines (merged rows from skewed photos) are re-split using K-Means clustering
- Each row is sorted by X-coordinate to form the column sequence
- The final result is a 16 × 7 data matrix of solder force values in Newtons

### 3) Data Cleaning (`data_cleaner.py`)

Raw OCR text is normalised to valid floats:

- Common OCR character substitutions corrected (e.g. `O` → `0`, `l` → `1`)
- Values outside configured bounds flagged as noise and zeroed
- Low-confidence tokens handled gracefully

### 4) Cross-Verification (`cross_verifier.py`)

When an optional Excel reference file is provided alongside the image:

- The OCR-extracted matrix is compared cell-by-cell against the Excel data
- A configurable tolerance (default ±0.05 N) determines per-cell match
- A minimum match percentage (default 95%) determines overall pass/fail
- The system selects the more reliable matrix (OCR vs Excel) for downstream QC

### 5) QC Rule Evaluation (`quality_rules.py`)

Three rules are evaluated against the 16 × 7 matrix:

| Rule | Condition | Default |
|------|-----------|---------|
| Rule A | At least 75% of all points must be > 0.8 N | 75% |
| Rule B | No more than 2 points per bus bar may be ≤ 0.35 N | 2 per bar |
| Rule C | No more than 8 total points (and ≤ 2 per bar) may be ≤ 0.1 N | 8 total |

### 6) Report Generation (`report_generator.py`)

An Excel workbook is produced for every batch containing:

- **Data Matrix sheet** — cleaned 16 × 7 values with colour coding by quality zone
- **QC Summary sheet** — rule-by-rule pass/fail with counts and thresholds
- **Verification sheet** — cell-level match table (when Excel reference provided)

---

## QC Decision Logic

The system produces one of the following outcomes:

| Decision | Condition |
|----------|-----------|
| `APPROVED` | All QC rules pass |
| `REJECTED` | One or more QC rules fail |
| `MANUAL_REVIEW_REQUIRED` | Structural issues; data may be partial |
| `DATA_ERROR` | Extraction failed entirely |
| `VERIFICATION_FAILED` | OCR vs Excel cross-check did not meet threshold |

Decision flow:

```
if extraction fails:
    DATA_ERROR
elif Excel verification fails (when reference provided):
    VERIFICATION_FAILED
elif all QC rules pass:
    APPROVED
elif any QC rule fails:
    REJECTED
else:
    MANUAL_REVIEW_REQUIRED
```

---

## Web Dashboard (`web_app.py`)

A FastAPI web application provides a browser-based interface with:

- **Dashboard** — file upload, pipeline result display, live system logs
- **Processed** — list of all successfully processed files with image preview
- **Reports** — downloadable Excel reports with per-report graph visualisation
- **Configuration** — live-editable QC thresholds and OCR parameters
- **About** — system overview

### Running the server

```bash
# From the QC_Automation directory
python -m uvicorn web_app:app --host 0.0.0.0 --port 8001 --reload
```

Open in browser: **http://localhost:8001**

---

## Project Structure

```
QC_Automation/
├── main.py               # Pipeline orchestration entry point
├── web_app.py            # FastAPI web dashboard
├── config.py             # Thresholds, paths, and feature flags
├── input_handler.py      # File routing and input detection
├── batch_manager.py      # Batch ID and lifecycle tracking
├── image_processor.py    # Crop, deskew, and preprocessing
├── ocr_engine.py         # GCP Vision OCR + matrix assembly
├── data_cleaner.py       # Noise removal and normalisation
├── validator.py          # Structural validation
├── quality_rules.py      # QC rule engine
├── cross_verifier.py     # Image vs Excel comparison
├── report_generator.py   # Excel report creation
├── excel_parser.py       # Excel matrix extraction
├── google_credentials.json  # GCP service account credentials
├── static/               # Frontend assets (HTML, CSS, JS)
├── models/               # Stored models directory
├── input/                # Incoming files (watch folder)
├── processed/            # Successfully processed files
├── failed/               # Files that could not be processed
├── output/               # Generated Excel reports
├── logs/                 # Application logs
├── debug/                # Debug overlay images
└── tests/                # Unit and integration tests
```

---

## Configuration (`config.py`)

All key parameters can be tuned without changing code:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `BUS_BARS` | Number of rows in the data grid | 16 |
| `POINTS_PER_BAR` | Number of columns per row | 7 |
| `RULE_A_THRESHOLD` | Minimum force for Rule A pass (N) | 0.8 |
| `RULE_A_MIN_PERCENTAGE` | Required fraction above Rule A threshold | 0.75 |
| `RULE_B_THRESHOLD` | Rule B failure threshold (N) | 0.35 |
| `MAX_RULE_B_PER_BAR` | Max Rule B failures per bus bar | 2 |
| `RULE_C_THRESHOLD` | Rule C failure threshold (N) | 0.1 |
| `MAX_RULE_C_TOTAL` | Max total Rule C failures | 8 |
| `VERIFY_TOLERANCE` | Cell match tolerance vs Excel (N) | 0.05 |
| `VERIFY_MATCH_THRESHOLD` | Minimum match % to pass verification | 0.95 |
| `MIN_OCR_CONFIDENCE` | Minimum GCP Vision symbol confidence | 0.85 |

---

## Setup

### Requirements

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Key dependencies:

- `fastapi` + `uvicorn` — web server
- `google-cloud-vision` — OCR engine
- `opencv-python` — image preprocessing
- `openpyxl` — Excel report generation
- `numpy` + `scikit-learn` — matrix reconstruction

### Google Cloud Vision Credentials

Place your GCP service account JSON file at:

```
QC_Automation/google_credentials.json
```

Obtain from: Google Cloud Console → APIs & Services → Credentials → Service Accounts.

Enable the **Cloud Vision API** on your project.

---

## Running the Batch Processor (CLI mode)

Process a single file directly without the web interface:

```bash
python main.py --once
```

---

## Report Output

Each generated Excel report contains:

| Sheet | Content |
|-------|---------|
| Data Matrix | 16 × 7 cleaned values, colour-coded by quality zone |
| QC Summary | Rule A/B/C results with pass/fail counts |
| Verification | Cell-by-cell OCR vs Excel comparison (when reference provided) |

---

## Decision Colour Coding

Values in the data matrix and dashboard are colour-coded:

| Zone | Range | Colour |
|------|-------|--------|
| Pass (A) | > 0.8 N | Green |
| Mid | 0.35 – 0.8 N | Blue |
| Borderline (B) | 0.1 – 0.35 N | Amber |
| Fail (C) | ≤ 0.1 N | Red |
