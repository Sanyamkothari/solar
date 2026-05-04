# Solar QC — User Manual

**System:** Solar QC Automated Solder Point Inspection  
**Version:** Production (Main Branch)  
**Interface:** Web Dashboard — http://localhost:8001  

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Getting Started](#2-getting-started)
3. [Dashboard — Running an Inspection](#3-dashboard--running-an-inspection)
4. [Understanding the Results](#4-understanding-the-results)
5. [Pipeline Steps Explained](#5-pipeline-steps-explained)
6. [Processed Files](#6-processed-files)
7. [Reports](#7-reports)
8. [Configuration](#8-configuration)
9. [QC Rules Reference](#9-qc-rules-reference)
10. [File Requirements](#10-file-requirements)
11. [Tips for Best OCR Results](#11-tips-for-best-ocr-results)
12. [Troubleshooting](#12-troubleshooting)
13. [System Logs](#13-system-logs)
14. [Folder Structure](#14-folder-structure)

---

## 1. System Overview

Solar QC is an automated quality control system for **solder point peel-force inspection**.

It accepts two types of input:
- **Images** — photographs or screenshots of the factory monitor showing the 16×7 peel-force data table
- **Excel files** — direct spreadsheet exports of the measurement data

The system extracts a **16 × 7 matrix** of solder force values (in Newtons), evaluates them against three configurable QC rules, and produces a **pass/fail decision** with a downloadable Excel report.

### What the system does NOT do

- It does not control factory equipment
- It does not modify the source image or Excel file
- It does not send data to any external service except Google Cloud Vision (for OCR)

---

## 2. Getting Started

### Starting the Server

Open a terminal in the `QC_Automation` directory and run:

```bash
python -m uvicorn web_app:app --host 0.0.0.0 --port 8001 --reload
```

Wait until you see:

```
INFO:     Application startup complete.
```

Then open your browser and navigate to:

> **http://localhost:8001**

### Prerequisites

Before using the system, ensure:

| Requirement | Location | Notes |
|-------------|----------|-------|
| Python dependencies installed | `requirements.txt` | Run `pip install -r requirements.txt` |
| Google Cloud credentials | `QC_Automation/google_credentials.json` | Required for OCR; get from GCP Console |
| Internet connection | — | Required for Google Cloud Vision API calls |

---

## 3. Dashboard — Running an Inspection

The **Dashboard** is your main working screen. It is split into two panels:

- **Left panel** — file upload and system logs
- **Right panel** — inspection results

### Step 1: Upload the Inspection File

You can provide the file in two ways:

**Drag & Drop**  
Drag your image (PNG/JPG) or Excel file (XLSX/XLS) directly onto the upload area labelled *"Drag & Drop or Browse Files"*.

**Browse**  
Click **Browse Files** to open a file picker and select your file.

The selected filename will appear below the upload area with a 📄 icon.

> **Supported formats:** `.png` `.jpg` `.jpeg` `.xlsx` `.xls`  
> **Maximum file size:** 50 MB

---

### Step 2: (Optional) Add a Reference Excel File

If you have an Excel spreadsheet from the same batch, you can attach it for **cross-verification**.

Click the second upload area labelled *"Optional: Reference Excel for Cross-Verification"* and select your `.xlsx` or `.xls` file.

When a reference file is provided:
- The system compares every cell of the OCR-extracted matrix against the Excel data
- A tolerance of ±0.05 N per cell is applied
- At least 95% of cells must match for verification to pass
- The most reliable matrix (OCR vs Excel) is used for QC rule evaluation

---

### Step 3: Start the Pipeline

Click **Start QC Pipeline →**

The button will change to *"Processing..."* with a spinner. Do not click again or navigate away.

Processing typically takes **5–30 seconds** depending on image complexity and network speed to Google Cloud Vision.

---

### Step 4: View the Result

Once complete, the right panel shows the inspection outcome. See [Section 4](#4-understanding-the-results) for a full explanation.

---

## 4. Understanding the Results

### Decision Banner

A coloured banner at the top of the results panel shows the overall outcome:

| Banner | Colour | Meaning |
|--------|--------|---------|
| ✅ **APPROVED** | Green | All three QC rules passed |
| ❌ **REJECTED** | Red | One or more QC rules failed |
| 🔍 **MANUAL\_REVIEW\_REQUIRED** | Amber | Data was extracted but structure is suspect; human review needed |
| ⚠️ **DATA\_ERROR** | Red | File could not be processed; no data was extracted |
| ⚠️ **VERIFICATION\_FAILED** | Amber | OCR vs Excel comparison fell below 95% match threshold |

### Data Source Pill

Below the banner, a small pill shows:
- The **Batch ID** (e.g. `BATCH_20260504_223015_A1B2C3D4`)
- The **Data Source** — either `OCR` (from image), `Excel` (from reference file), or `N/A` (if extraction failed)

When cross-verification is active, the source indicates which matrix was selected as more reliable.

---

### Cross-Verification Section

Only visible when a reference Excel file was provided.

| Field | Description |
|-------|-------------|
| Match Rate | Percentage of cells within tolerance |
| Matched Cells | e.g. `106/112` — cells within ±0.05 N |
| Mismatches | Number of cells that differ beyond tolerance |

---

### Pipeline Steps

A step-by-step log of what happened during processing:

| Step | Possible Outcomes |
|------|-------------------|
| 📁 File Detection | ✅ PASS — file found and valid |
| 🔄 Extraction | ✅ PASS / ❌ FAIL — OCR or Excel parsing |
| 🔄 Cross-Verification | ✅ PASS / ❌ FAIL — only shown if Excel reference provided |
| 📊 QC Evaluation | ✅ PASS / ❌ FAIL — rule engine result |
| 📦 File Moved | ⚠️ MOVED — file moved to `processed/` or `failed/` |

Each step shows a **timestamp** (HH:MM:SS) in the right column.

---

### Extracted Data Matrix

A colour-coded table of the 16 × 7 solder force values (in Newtons):

| Cell Colour | Range | Meaning |
|------------|-------|---------|
| 🟢 Green | > 0.8 N | Strong bond — passes Rule A |
| 🔵 Blue | 0.35 – 0.8 N | Acceptable mid-range |
| 🟡 Amber | 0.1 – 0.35 N | Low force — counts against Rule B |
| 🔴 Red | ≤ 0.1 N | Critical failure — counts against Rule C |

Rows are **Bus Bars** (Bar 1 – Bar 16).  
Columns are **Measurement Points** (P1 – P7).

---

### Rule Summary

A three-row table showing each rule's result:

| Column | Description |
|--------|-------------|
| Rule | Rule A / B / C |
| Passed | ✅ Yes or ❌ No |
| Detail | Count vs. threshold (e.g. `84/84 req.`) |

---

## 5. Pipeline Steps Explained

### Image Path

```
Upload → File Size Check → Image Preprocessing → Google Cloud Vision OCR
       → Matrix Reconstruction → Data Cleaning → Validation
       → QC Rules → Report Generation → Move to Processed
```

### Excel Path

```
Upload → File Size Check → Excel Parser → Data Cleaning → Validation
       → QC Rules → Report Generation → Move to Processed
```

### What happens on failure

If any step fails (e.g. OCR error, file too corrupted), the pipeline stops immediately and:
- Sets decision to `DATA_ERROR`
- Moves the file to the `failed/` folder with the Batch ID prefix
- Logs the error in `logs/qc_run.log`

---

## 6. Processed Files

Navigate to **Processed** in the left sidebar.

This page lists every file that successfully completed the QC pipeline.

| Column | Description |
|--------|-------------|
| File Name | Includes the Batch ID prefix |
| Size | File size in KB or MB |
| Date | Date and time of processing |
| 👁 Eye button | Preview image files in a lightbox |

Click **Refresh** (↻ button) to reload the list.

> Files are **never deleted** automatically. They remain in `processed/` indefinitely.

---

## 7. Reports

Navigate to **Reports** in the left sidebar.

This page lists all generated Excel inspection reports.

### Viewing a Report

Click the **📈 chart icon** next to any report to open the visual report detail view.

The report detail shows:

**Summary statistics:**
- Total Points inspected
- Mean force value
- Minimum and Maximum values

**Four charts:**

| Chart | Description |
|-------|-------------|
| Average Solder Force per Bus Bar | Bar chart — one bar per bus bar, coloured by quality zone |
| Value Distribution (Quality Zones) | Doughnut chart — proportion of points in each zone |
| Average Force per Point Position | Line chart — average force per column position (P1–P7) |
| Heatmap — All Solder Points | Colour-coded grid of the full 16×7 matrix |

### Downloading

| Action | Button |
|--------|--------|
| Download Charts (PNG) | **Download Charts** button |
| Download Excel Report | **Download Excel** button |

### Excel Report Contents

The downloaded `.xlsx` file contains up to 3 sheets:

| Sheet | Contents |
|-------|----------|
| Data Matrix | 16×7 table of cleaned force values with conditional formatting |
| QC Summary | Rule A/B/C results with pass/fail counts and thresholds |
| Verification | Cell-by-cell comparison with Excel reference (only if provided) |

---

## 8. Configuration

Navigate to **Configuration** in the sidebar.

This screen lets you edit QC thresholds and processing parameters **live without restarting the server**.

### Editable Parameters

#### Data Structure

| Field | Description | Default |
|-------|-------------|---------|
| Bus Bars | Number of rows expected in the data grid | 16 |
| Points / Bar | Number of measurement points per bus bar | 7 |
| Total Points | Auto-calculated (Bus Bars × Points / Bar) | 112 |

#### Quality Thresholds

| Field | Description | Default |
|-------|-------------|---------|
| Rule A (>N) | Minimum force to count as a passing point | 0.8 N |
| Rule A min % | Fraction of total points that must exceed Rule A threshold | 0.75 (75%) |
| Rule A min points | Auto-calculated | 84 |
| Rule B (≤N) | Force at or below which a point counts against Rule B | 0.35 N |
| Rule B max/bar | Max Rule B failures allowed per single bus bar | 2 |
| Rule C (≤N) | Force at or below which a point counts against Rule C | 0.1 N |
| Rule C max total | Maximum total Rule C failures across all bars | 8 |
| Rule C max/bar | Maximum Rule C failures in a single bar | 1 |

#### OCR Settings

| Field | Description | Default |
|-------|-------------|---------|
| Min Confidence | Minimum GCP Vision symbol confidence to accept a reading | 0.85 |
| Value Min (N) | Minimum plausible force value; below this = OCR noise | 0.0 N |
| Value Max (N) | Maximum plausible force value; above this = OCR noise | 10.0 N |

#### Verification

| Field | Description | Default |
|-------|-------------|---------|
| Tolerance (±) | Maximum per-cell difference allowed between OCR and Excel | 0.05 N |
| Match Threshold | Minimum fraction of cells that must match to pass verification | 0.95 (95%) |

### Saving Changes

After editing any value, the **Save Changes** button becomes active. Click it to apply the new values immediately. A green toast notification confirms success.

> ⚠️ **Important:** Changes apply to the next batch processed, not retroactively to past reports.

---

## 9. QC Rules Reference

The system evaluates three rules in order. All three must pass for `APPROVED`.

---

### Rule A — Minimum Bond Strength

**Question:** Are enough solder points strong enough?

**Logic:**  
At least **75%** of all 112 points must have a peel force **greater than 0.8 N**.  
That means at least **84 points** must exceed 0.8 N.

**Fails if:** Fewer than 84 points are above 0.8 N.

---

### Rule B — Low-Force Warning per Bar

**Question:** Is any single bus bar showing too many weak bonds?

**Logic:**  
For each of the 16 bus bars, count how many points have a force **at or below 0.35 N**.  
No single bar may have **more than 2** such points.

**Fails if:** Any one bus bar has 3 or more points ≤ 0.35 N.

---

### Rule C — Critical Failure Threshold

**Question:** Are there any critically weak solder points?

**Logic:**  
Count all points with a force **at or below 0.1 N** across the entire matrix.  
The total must not exceed **8**, AND no single bar may have **more than 1** such point.

**Fails if:** Total critical failures > 8, OR any single bar has > 1 critical failure.

---

### Decision Matrix

| Rule A | Rule B | Rule C | Decision |
|--------|--------|--------|----------|
| ✅ Pass | ✅ Pass | ✅ Pass | **APPROVED** |
| ❌ Fail | any | any | **REJECTED** |
| any | ❌ Fail | any | **REJECTED** |
| any | any | ❌ Fail | **REJECTED** |

---

## 10. File Requirements

### Images (PNG / JPG / JPEG)

| Requirement | Details |
|-------------|---------|
| Content | Must show a 16×7 solder force data table on a monitor screen |
| Orientation | Portrait or landscape; slight rotation is auto-corrected |
| Minimum resolution | ~800×600 pixels recommended for reliable OCR |
| Maximum file size | 50 MB |
| Accepted formats | `.png`, `.jpg`, `.jpeg` |

**Good images:**
- Clear, in-focus photograph of the monitor
- Data table fully visible within the frame
- Reasonable lighting — no heavy glare or shadow over the numbers

**Problematic images (may fail or reduce accuracy):**
- Extreme blur or motion shake
- Data table partially cut off
- Very strong reflections obscuring digits
- Heavy JPEG compression artifacts

---

### Excel Files (XLSX / XLS)

| Requirement | Details |
|-------------|---------|
| Content | Must contain the 16×7 numeric matrix in a recognisable tabular layout |
| Values | Numeric float values in Newtons |
| Maximum file size | 50 MB |
| Accepted formats | `.xlsx`, `.xls` |

---

### Reference Excel (Cross-Verification)

The optional reference Excel is used only for **comparison** — it does not replace the main inspection file. It must contain the same 16×7 matrix from the same batch.

---

## 11. Tips for Best OCR Results

### Photography Tips

1. **Hold the camera steady** — use both hands or rest it on a surface
2. **Fill the frame** — the data table should occupy at least 60% of the image
3. **Avoid glare** — tilt the camera slightly to avoid monitor reflections
4. **Use good lighting** — avoid inspecting in direct sunlight hitting the screen
5. **Focus the camera** — wait for autofocus to lock before taking the photo
6. **Keep it portrait** — the table reads better in portrait orientation

### Screenshot Tips

If you can take a screenshot directly from the factory computer, this is always more reliable than a phone photo:

- Use the system's built-in screenshot tool (PrtSc / Snipping Tool / Shift+Cmd+4)
- Crop tightly around the data table before uploading
- PNG format is preferred over JPEG for screenshots (lossless)

### If OCR Keeps Failing

1. Try a screenshot instead of a photo
2. Increase lighting and retake
3. Ensure the full 16 rows and 7 columns are visible
4. Check the `logs/qc_run.log` for the specific error message
5. Check the `debug/` folder — a debug overlay image is saved showing what the preprocessor cropped

---

## 12. Troubleshooting

### "Could not extract data from file" (DATA\_ERROR)

**Most common causes:**

| Cause | Solution |
|-------|----------|
| Google Cloud Vision API timeout | Wait 30 seconds and try again; the system auto-retries once |
| Image has no readable data table | Ensure the monitor is displaying the 16×7 peel-force table |
| Image too blurry | Retake with a steady hand or use a screenshot |
| Google credentials missing | Check `google_credentials.json` exists in `QC_Automation/` |
| No internet connection | Ensure the machine has internet access |

---

### "Request failed: Failed to fetch"

**Cause:** The browser is connected to the wrong server address.

**Solution:** Make sure you are on **http://localhost:8001** (not 8000 or any other port).

---

### "Unsupported file type"

**Cause:** File extension is not in the supported list.

**Solution:** Only upload `.png`, `.jpg`, `.jpeg`, `.xlsx`, or `.xls` files.

---

### "Uploaded file is too large"

**Cause:** File exceeds 50 MB.

**Solution:** Compress the image (reduce resolution) or export a lighter Excel file.

---

### Processing takes more than 60 seconds

**Cause:** Google Cloud Vision is slow or experiencing high load.

**What happens:** The system will automatically retry once with a 120-second timeout.

**If it still fails:** Try again in a few minutes. This is an external API issue.

---

### APPROVED result but numbers look wrong

**Cause:** OCR may have misread some digits (e.g. `0` misread as `O`, `1` misread as `l`).

**Solution:**
- Upload the Excel reference file for cross-verification
- Check the `debug/` folder for a preprocessed image overlay
- Review the extracted matrix carefully against the on-screen values
- If discrepancies are systematic, contact the administrator to adjust `MIN_OCR_CONFIDENCE` in Configuration

---

### Server won't start

**Common causes and fixes:**

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `Port already in use` | Kill any existing process on port 8001 or change the port |
| `google_credentials.json not found` | Place the GCP service account JSON in `QC_Automation/` |
| `Address already in use` | A previous server is still running; restart your terminal |

---

## 13. System Logs

### Live Logs Panel

The **Dashboard** shows live system logs in the terminal-style panel at the bottom left. These auto-refresh every 5 seconds.

Logs show:
- Batch IDs and timestamps for each processed file
- Step-by-step processing messages
- Any errors encountered

### Log Files

Persistent logs are written to:

```
QC_Automation/logs/qc_run.log
```

Daily rotation is applied — past logs are kept as `qc_run.log.YYYYMMDD`.

**Log levels:**

| Level | Meaning |
|-------|---------|
| `INFO` | Normal operation message |
| `WARNING` | Non-critical issue (e.g. partial matrix detected) |
| `ERROR` | Processing failure — inspect this for troubleshooting |

---

## 14. Folder Structure

```
QC_Automation/
│
├── input/          ← Drop files here for batch processing (watched folder)
│
├── processed/      ← Files that completed the QC pipeline successfully
│                     Format: BATCH_YYYYMMDD_HHMMSS_XXXXXXXX_original_filename.ext
│
├── failed/         ← Files that could not be processed
│                     Same naming format as processed/
│
├── output/         ← Generated Excel reports
│                     Format: QC_BATCH_YYYYMMDD_HHMMSS_XXXXXXXX.xlsx
│
├── logs/           ← Application logs
│   ├── qc_run.log              ← Current log
│   └── qc_run.log.YYYYMMDD    ← Daily rotated logs
│
├── debug/          ← Debug overlay images showing preprocessing crop box
│                     Useful when OCR fails to understand what was sent to GCP
│
├── models/         ← Model storage directory
│
└── google_credentials.json  ← GCP service account credentials (required)
```

### Batch ID Format

Every inspection is assigned a unique Batch ID:

```
BATCH_20260504_223015_A1B2C3D4
        │       │      │
        │       │      └── Random 8-character hex suffix (ensures uniqueness)
        │       └── Time: HH MM SS
        └── Date: YYYY MM DD
```

All files related to a batch share this prefix:
- `processed/BATCH_20260504_223015_A1B2C3D4_screenshot.png`
- `output/QC_BATCH_20260504_223015_A1B2C3D4.xlsx`

---

## Quick Reference Card

| Action | How |
|--------|-----|
| Start server | `python -m uvicorn web_app:app --host 0.0.0.0 --port 8001` |
| Open dashboard | http://localhost:8001 |
| Run inspection | Dashboard → Upload file → Start QC Pipeline |
| Add Excel reference | Dashboard → Upload to second drop zone |
| View past files | Sidebar → Processed |
| Download report | Sidebar → Reports → Download Excel |
| View charts | Sidebar → Reports → Click 📈 icon |
| Edit thresholds | Sidebar → Configuration → Save Changes |
| View logs | Dashboard → System Logs panel (auto-refreshes) |
| Find raw logs | `QC_Automation/logs/qc_run.log` |
| Debug failed OCR | `QC_Automation/debug/` folder |

---

*Solar QC User Manual — Solar Panel Manufacturing QC Division*
