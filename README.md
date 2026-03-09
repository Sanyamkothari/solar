# Solar Panel QC Automation System

## Overview
The **Solar Panel QC Automation System** automates the quality control (QC) process for solar panel inspection reports. In solar manufacturing environments, inspection reports often contain module matrices, serial numbers, electrical measurements, and other important parameters that must be verified before panels are deployed.

Manual verification of these inspection reports is time-consuming, prone to human error, and difficult to scale when dealing with large volumes of solar panel production data.

This project automates the QC workflow by:
- Extracting inspection data using **Optical Character Recognition (OCR)**
- Cleaning and structuring the extracted information
- Applying **rule-based validation checks**
- Cross-verifying values with reference data
- Automatically generating structured **QC reports**

The system improves efficiency, reduces manual effort, and enables scalable verification of solar panel inspection data.

---

## Features

### 🔍 OCR & Data Extraction
- **Google Cloud Vision API** integration for high-accuracy text recognition
- **K-Means clustering** algorithm for intelligent grid reconstruction from skewed photos
- Support for real-world factory photos (phone cameras capturing monitor screens)
- Automatic detection and extraction of **16×7 measurement matrices** (112 data points)
- Handles partial matrices (minimum 5 bus bars) for cropped inspection images

### 🖼️ Advanced Image Preprocessing
- **Automatic cropping** to focus on data regions
- **Deskewing and rotation correction** for misaligned photos
- **Perspective correction** for angled camera shots
- **CLAHE (Contrast Limited Adaptive Histogram Equalization)** for improved readability
- **Denoising filters** to remove compression artifacts and noise
- **Adaptive sharpening** for enhanced text clarity

### 🧹 Data Cleaning & Validation
- Intelligent **noise removal** and formatting correction
- **Structural validation** ensuring correct matrix dimensions (16 bus bars × 7 points)
- **Data bounds checking** (0.0-10.0 N peel force range)
- **Proportional scaling** for partial matrix evaluation
- Handles OCR errors and formatting inconsistencies automatically

### ✅ Multi-Level Quality Rules Engine
- **Rule A**: Minimum 75% of points must exceed 0.8N peel force threshold
- **Rule B**: Maximum 2 points ≤ 0.35N allowed per bus bar
- **Rule C**: Maximum 8 points ≤ 0.1N total across all bars (max 1 per bar)
- Proportional rule application for partial matrices
- Detailed per-rule evaluation reports

### 🔄 Cross-Verification System
- **Image vs Excel comparison** for data accuracy validation
- Cell-by-cell comparison with **0.05N tolerance**
- **95% match threshold** requirement for verification pass
- Detailed mismatch reports showing:
  - Bar and point locations
  - Image vs Excel value differences
  - Per-bar mismatch summaries
- Prevents false positives from OCR errors

### 📊 Interactive Streamlit Dashboard
- **Multi-tab interface** for comprehensive factory operations:
  - **📤 Upload Tab**: Drag-and-drop file processing with live pipeline visualization
  - **📜 History Tab**: Complete batch processing history with filtering
  - **📈 Analytics Tab**: Interactive charts showing pass/fail trends, quality metrics
  - **👁️ Monitoring Tab**: Real-time activity feed and system status
  - **⚙️ Config Tab**: Live configuration display and documentation
- **Real-time processing feedback** with step-by-step status updates
- **Decision banners** with color-coded results (APPROVED/REJECTED/MANUAL_REVIEW)
- **Downloadable reports** directly from the dashboard
- **Responsive design** optimized for factory floor usage

### 🗂️ Batch Management & Organization
- **Unique batch ID generation** (timestamp + UUID) for traceability
- **Sequential processing** to prevent resource conflicts
- **Automatic file organization**:
  - `input/` → New inspection files
  - `processed/` → Successfully processed files
  - `failed/` → Files with errors
  - `output/` → Generated QC reports
- **Comprehensive logging** with rotation and size limits
- **Context tracking** throughout entire pipeline

### 📑 Comprehensive Report Generation
- **Excel QC reports** with professional formatting
- **Multi-sheet reports** containing:
  - Extracted data matrix
  - Quality rule evaluation results
  - Cross-verification reports (when applicable)
  - Error flags and warnings
  - Processing metadata and timestamps
- **Decision categories**:
  - ✅ **APPROVED**: All rules passed
  - ❌ **REJECTED**: One or more rules failed
  - ⚠️ **MANUAL_REVIEW_REQUIRED**: Partial data or warnings
  - 🔴 **DATA_ERROR**: Structural validation failed
  - 🔄 **VERIFICATION_FAILED**: Image-Excel mismatch detected

### 🛡️ Error Handling & Recovery
- **Graceful failure handling** with detailed error messages
- **Automatic file quarantine** for problematic inputs
- **Validation exceptions** with actionable feedback
- **Step-by-step error localization** for troubleshooting
- **File size limits** (50MB) to prevent memory issues

### 🔧 Flexible Configuration
- Centralized configuration in `config.py`
- Adjustable quality thresholds without code changes
- Configurable image preprocessing parameters
- Customizable directory structure
- Environment-specific settings support

---

## Core Functionality

### 📥 Input Processing
The system accepts multiple input formats:
- **Images**: JPEG, PNG (factory photos of test equipment screens)
- **Excel Files**: Reference data for cross-verification (.xlsx, .xls)
- **Supported scenarios**:
  - Phone camera photos of monitor displays
  - Screenshot captures from test equipment
  - Scanned inspection reports
  - WhatsApp images and compressed photos

### 🔬 OCR Extraction Process
1. **Image Loading**: Accepts raw images via file upload or directory monitoring
2. **Preprocessing Pipeline**:
   - Automatic cropping to relevant data region
   - Perspective correction for angled shots
   - Deskewing for rotated images
   - Contrast enhancement (CLAHE)
   - Noise reduction and sharpening
3. **Google Cloud Vision API**:
   - Submits preprocessed image for text detection
   - Extracts text annotations with bounding boxes
   - Captures confidence scores for quality assessment
4. **K-Means Grid Reconstruction**:
   - Clusters detected text by Y-coordinates to identify rows
   - Sorts text within each row by X-coordinates
   - Reconstructs the 16×7 matrix structure
   - Handles partial matrices (minimum 5 bus bars)

### 🧼 Data Cleaning & Structuring
- **Pattern recognition**: Identifies numeric values using regex
- **Unit stripping**: Removes "N", "kN" and other measurement units
- **Format normalization**: Converts various number formats (1,23 → 1.23)
- **Outlier detection**: Flags values outside 0.0-10.0 N range
- **Matrix assembly**: Constructs numerical matrix from cleaned values
- **Gap filling**: Handles missing or unreadable cells

### ✔️ Validation & Quality Evaluation
**Structural Validation**:
- Verifies matrix dimensions (16 bus bars × 7 points expected)
- Accepts partial matrices (≥5 bus bars) with proportional rule scaling
- Checks data types and value ranges
- Raises clear exceptions for structural errors

**Quality Rules Application**:
- **Rule A Evaluation**: Counts points above 0.8N, ensures ≥75% threshold
- **Rule B Evaluation**: Checks each bus bar for points ≤0.35N (max 2 allowed)
- **Rule C Evaluation**: Total points ≤0.1N must not exceed 8 (max 1 per bar)
- **Proportional scaling**: Adjusts thresholds for partial matrices

**Decision Logic**:
```
IF structural_validation_fails:
    → DATA_ERROR
ELIF cross_verification_enabled AND verification_fails:
    → VERIFICATION_FAILED
ELIF all_rules_pass:
    → APPROVED
ELIF any_rule_fails:
    → REJECTED
ELSE:
    → MANUAL_REVIEW_REQUIRED
```

### 🔍 Cross-Verification (Optional)
When Excel reference data is provided:
1. **Matrix Extraction**: Parses Excel file to extract reference matrix
2. **Dimension Matching**: Aligns OCR matrix with Excel matrix
3. **Cell-by-Cell Comparison**:
   - Calculates absolute difference for each cell
   - Flags mismatches exceeding 0.05N tolerance
   - Records location, values, and difference magnitude
4. **Match Ratio Calculation**: Computes percentage of matching cells
5. **Threshold Check**: Requires ≥95% match for verification pass
6. **Report Generation**: Detailed mismatch report with per-bar summaries

### 📋 Report Generation
Generated Excel reports include:
- **Sheet 1: Extracted Matrix**: Complete data grid with formatting
- **Sheet 2: Quality Evaluation**: Rule-by-rule results and statistics
- **Sheet 3: Verification Report**: Mismatch details (if applicable)
- **Metadata**: Batch ID, file name, timestamps, processing status
- **Visual indicators**: Color-coded cells for pass/fail/warnings

### 🔄 Batch Processing
- **Directory monitoring**: Continuous scan of input folder
- **FIFO processing**: Files processed in order of arrival
- **Isolation**: Each file processed independently with unique batch ID
- **File routing**:
  - Success → `processed/` directory + report in `output/`
  - Failure → `failed/` directory with error logs
- **Logging**: Comprehensive logs in `logs/` with rotation

### 🎯 Dashboard Operations
**Upload & Process**:
- Drag-and-drop file upload
- Optional Excel reference file for cross-verification
- Live pipeline visualization with step-by-step progress
- Real-time status updates (⏳ Running, ✅ Pass, ❌ Fail)
- Downloadable result reports

**History & Analytics**:
- Searchable batch history with filtering
- Pass/fail trend charts
- Quality metrics visualization
- Per-rule success rate analysis
- Processing time statistics

**Monitoring**:
- Live activity feed showing recent processing events
- System status indicators
- Directory file counts
- Real-time alerts for failures

---

## System Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  Input Files (Images/Excel)                                 │
│  └─ input/ directory or Dashboard upload                    │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  📁 Input Handler                                           │
│  └─ File detection, routing (image vs Excel)               │
│     File size & format validation                           │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  🆔 Batch Manager                                           │
│  └─ Generate unique Batch ID                                │
│     Initialize processing context & logging                 │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  🖼️ Image Preprocessor                                      │
│  └─ Crop → Deskew → Denoise → CLAHE → Sharpen             │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  👁️ OCR Engine (Google Cloud Vision)                       │
│  └─ Text detection with bounding boxes                      │
│     K-Means clustering → Grid reconstruction                │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  🧹 Data Cleaner                                            │
│  └─ Noise removal, unit stripping, format normalization    │
│     Matrix assembly (16×7 or partial)                       │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  ✔️ Validator                                               │
│  └─ Structural validation (rows/columns)                    │
│     Data bounds checking, partial matrix support            │
└────────────────────────┬────────────────────────────────────┘
                         ▼
        ┌────────────────┴─────────────────┐
        │                                  │
        ▼ (if Excel provided)              ▼ (skip if image-only)
┌─────────────────────┐           ┌────────────────────────────┐
│  🔄 Cross Verifier  │           │  Direct to Quality Rules   │
│  └─ Image vs Excel  │           └────────────────────────────┘
│     Cell comparison │                    │
│     95% threshold   │                    │
└──────────┬──────────┘                    │
           │                                │
           └────────────────┬───────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  📏 Quality Evaluator                                       │
│  └─ Rule A: 75% points > 0.8N                              │
│     Rule B: Max 2 points ≤ 0.35N per bar                   │
│     Rule C: Max 8 points ≤ 0.1N total                      │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  🧠 Decision Engine                                         │
│  └─ APPROVED / REJECTED / MANUAL_REVIEW / DATA_ERROR       │
│     VERIFICATION_FAILED                                     │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  📑 Report Generator                                        │
│  └─ Multi-sheet Excel report generation                     │
│     Matrix + Quality + Verification + Metadata              │
└────────────────────────┬────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  📤 Output & File Management                                │
│  └─ Save report to output/                                  │
│     Move processed file to processed/ or failed/            │
│     Update logs and history                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
solar/
│
├── 📄 Core Pipeline Modules
│   ├── main.py                    # Main orchestrator & pipeline coordinator
│   ├── config.py                  # Centralized configuration & constants
│   ├── input_handler.py           # File detection & routing
│   ├── batch_manager.py           # Batch lifecycle management
│   ├── ocr_engine.py              # Google Cloud Vision OCR + K-Means
│   ├── image_processor.py         # Image preprocessing pipeline
│   ├── data_cleaner.py            # Data cleaning & normalization
│   ├── validator.py               # Structural validation
│   ├── quality_rules.py           # Quality rules engine (A, B, C)
│   ├── cross_verifier.py          # Image-Excel verification
│   ├── report_generator.py        # Excel report generation
│   ├── excel_parser.py            # Excel reference data parser
│   └── logger.py                  # Structured logging system
│
├── 🖥️ User Interface
│   └── dashboard.py               # Streamlit web dashboard
│
├── 🔐 Credentials (not in repo)
│   └── google_credentials.json    # Google Cloud Vision API key
│
├── 📂 Processing Directories
│   ├── input/                     # Drop new inspection files here
│   ├── processed/                 # Successfully processed files
│   ├── failed/                    # Files with processing errors
│   ├── output/                    # Generated QC reports (.xlsx)
│   ├── logs/                      # Application logs with rotation
│   └── input_images/              # Sample input images (optional)
│
├── 🧪 Testing
│   ├── tests/
│   │   ├── test_comprehensive.py  # End-to-end pipeline tests
│   │   └── test_factory_qc.py     # Unit tests for QC rules
│   ├── test_ocr.py                # OCR engine testing
│   └── test_ocr_result.txt        # Sample OCR output
│
├── 📋 Debug & Documentation
│   ├── README.md                  # This file
│   ├── ocr_debug*.txt             # OCR debugging outputs
│   ├── gcp_debug*.txt             # GCP integration debugging
│   └── debug_preprocessed.jpg     # Sample preprocessed image
│
└── 🔧 Configuration Files
    └── requirements.txt           # Python dependencies
```

---

## Module Description

### 🎯 **main.py**
Main orchestrator coordinating the entire QC automation pipeline.
- **`process_file()`**: Core function processing a single inspection file
- **Step-by-step execution**: File detection → Extraction → Validation → Quality rules → Verification → Report generation
- **Error handling**: Catches and categorizes exceptions at each stage
- **Live callbacks**: Supports real-time status updates for dashboard integration
- **Return structure**: Complete result dictionary with batch ID, steps, matrix, evaluation, and decision

### 📁 **input_handler.py** 
Smart file detection and routing component.
- **File type detection**: Distinguishes between images and Excel files
- **Format support**: JPEG, PNG, BMP for images; XLSX, XLS for Excel
- **Size validation**: Enforces 50MB file size limit
- **Path handling**: Works with both `pathlib.Path` and string paths
- **Error prevention**: Validates file existence and readability before processing

### 🗂️ **batch_manager.py**
Manages batch lifecycle and context tracking.
- **Unique ID generation**: Timestamp + UUID format (BATCH_YYYYMMDD_HHMMSS_XXXXXXXX)
- **Context management**: Maintains processing context throughout pipeline
- **Structured logging**: Batch-specific log entries with consistent formatting
- **File organization**: Handles file movement between input/processed/failed directories
- **Statistics tracking**: Maintains counters for processed/failed batches

### 👁️ **ocr_engine.py**
Google Cloud Vision-based OCR extraction engine.
- **GCP Integration**: Uses service account authentication (google_credentials.json)
- **Cached client**: Reuses Vision API client for performance
- **K-Means clustering**: Groups text by Y-coordinates to reconstruct table rows
- **Grid assembly**: Sorts and organizes detected text into 16×7 matrix
- **Confidence scoring**: Tracks OCR confidence levels
- **Error handling**: Graceful fallback for API errors or missing credentials
- **Partial matrix support**: Handles incomplete grids (minimum 5 rows)

### 🖼️ **image_processor.py**
Advanced image preprocessing pipeline.
- **Auto-cropping**: Removes irrelevant borders and focuses on data region
- **Deskewing**: Detects and corrects image rotation using Hough Line Transform
- **Perspective correction**: Identifies and warps quadrilateral data regions
- **CLAHE**: Contrast Limited Adaptive Histogram Equalization for clarity
- **Denoising**: Non-local means denoising to remove compression artifacts
- **Adaptive sharpening**: Enhances text edges without over-sharpening
- **Configurable parameters**: All thresholds specified in config.py

### 🧹 **data_cleaner.py**
Intelligent data cleaning and normalization.
- **Regex patterns**: Extracts numeric values from mixed text
- **Unit handling**: Strips "N", "kN", "Newton" and other units
- **Format conversion**: Handles comma/period decimal separators
- **Range validation**: Filters out-of-bounds values (0.0-10.0 N)
- **Matrix construction**: Assembles 2D list structure from cleaned values
- **Error recovery**: Handles OCR misreads and formatting inconsistencies
- **Logging**: Reports cleaning statistics and anomalies

### ✔️ **validator.py**
Strict structural validation enforcement.
- **Hard validation**: Raises `ValidationError` for critical failures
- **Soft warnings**: Returns `ValidationWarning` for non-critical issues
- **Dimension checking**: Verifies 16 rows × 7 columns (or partial with ≥5 rows)
- **Column consistency**: Ensures all rows have exactly 7 points
- **Type validation**: Confirms all values are numeric (float)
- **Matrix bounds**: Validates reasonable measurement ranges
- **Clear exceptions**: Provides actionable error messages for debugging

### 📏 **quality_rules.py**
Manufacturing quality criteria evaluation engine.
- **Rule A implementation**: Counts points above 0.8N, enforces 75% threshold
- **Rule B implementation**: Per-bar validation (max 2 points ≤ 0.35N)
- **Rule C implementation**: Global + per-bar limits for critical low values (≤0.1N)
- **Proportional scaling**: Adjusts thresholds for partial matrices
- **Detailed reporting**: Returns counts, thresholds, and pass/fail status per rule
- **`QualityEvaluator` class**: Static methods for each rule evaluation
- **Final decision**: Combines all rule results into overall QC status

### 🔄 **cross_verifier.py**
Image-to-Excel verification module.
- **Cell-by-cell comparison**: Compares OCR matrix with Excel reference
- **Tolerance handling**: 0.05N absolute difference threshold per cell
- **Match ratio calculation**: Computes percentage of matching cells
- **Mismatch tracking**: Records location, values, and difference for each discrepancy
- **Per-bar summaries**: Aggregates mismatches by bus bar
- **95% threshold**: Requires ≥95% cell match for verification pass
- **Detailed reports**: Returns structured verification dictionary with all mismatches

### 📑 **report_generator.py**
Excel report creation and formatting.
- **Multi-sheet workbook**: Separate sheets for matrix, quality, verification, metadata
- **Professional formatting**: Color-coded cells, borders, headers
- **Matrix visualization**: Displays extracted data in original 16×7 grid
- **Rule results**: Detailed breakdown of each quality rule evaluation
- **Verification details**: Complete mismatch listings (if applicable)
- **Metadata section**: Batch ID, filename, timestamps, decision
- **File naming**: BATCH_YYYYMMDD_HHMMSS_XXXXXXXX_Report.xlsx
- **Error resilience**: Handles partial data or missing sections gracefully

### 🖥️ **dashboard.py**
Streamlit-based interactive web dashboard.
- **Page config**: Wide layout, custom title and icon
- **Custom CSS**: Professional dark theme with gradient cards
- **Tab 1 - Upload**: Drag-and-drop file upload with live processing pipeline
  - Real-time step visualization (⏳ Running, ✅ Pass, ❌ Fail)
  - Optional Excel cross-verification upload
  - Decision banner with color-coded results
  - Download button for generated reports
- **Tab 2 - History**: Searchable batch processing history
  - Filterable table with batch ID, filename, decision, timestamp
  - Color-coded decision badges
  - Re-download past reports
- **Tab 3 - Analytics**: Interactive charts and metrics
  - Pass/fail trend line charts
  - Decision distribution pie charts
  - Average processing time statistics
  - Rule-by-rule success rates
- **Tab 4 - Monitoring**: Real-time system status
  - Live activity feed with recent processing events
  - Directory file counts (input/processed/failed/output)
  - System health indicators
- **Tab 5 - Config**: Live configuration viewer
  - Quality rule thresholds display
  - Image preprocessing parameters
  - Verification settings
  - Helpful documentation links

### ⚙️ **config.py**
Centralized configuration management.
- **Directory paths**: INPUT_DIR, PROCESSED_DIR, FAILED_DIR, OUTPUT_DIR, LOGS_DIR
- **Matrix structure**: BUS_BARS (16), POINTS_PER_BAR (7), TOTAL_POINTS (112)
- **Quality thresholds**: RULE_A/B/C thresholds and percentages
- **OCR settings**: Confidence minimums, data bounds
- **Image processing**: Crop regions, deskew angles, CLAHE parameters
- **Verification settings**: VERIFY_TOLERANCE (0.05N), VERIFY_MATCH_THRESHOLD (95%)
- **Decision categories**: APPROVED, REJECTED, MANUAL_REVIEW, DATA_ERROR, VERIFICATION_FAILED
- **File limits**: MAX_FILE_SIZE_BYTES (50MB)
- **Logging config**: Rotation size and backup counts
- **Easy customization**: Single file to adjust all system behavior

### 📝 **logger.py**
Structured logging system.
- **File rotation**: Automatic log rotation at 10MB with 5 backups
- **Dual output**: Console (INFO+) and file (DEBUG+) handlers
- **Structured formatting**: Timestamp, level, module, message
- **Batch context**: Includes batch ID in log entries
- **Error tracking**: Captures stack traces for exceptions
- **Performance logging**: Records processing times and statistics

### 📋 **excel_parser.py**
Excel reference data extraction.
- **Sheet detection**: Automatically finds data sheet in workbook
- **Header identification**: Locates matrix start position
- **Data extraction**: Reads 16×7 grid into structured format
- **Format handling**: Works with merged cells, formulas, formatted numbers
- **Error handling**: Validates Excel structure and content
- **Robust parsing**: Handles various Excel file layouts and styles

---

## Installation

### Prerequisites

- **Python 3.8 or higher**
- **pip** package manager
- **Google Cloud Platform account** with Vision API enabled
- **Service account credentials** (JSON key file)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd solar
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Google Cloud Vision API Setup

1. **Create a GCP Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one

2. **Enable Vision API**:
   - Navigate to **APIs & Services → Library**
   - Search for "Cloud Vision API"
   - Click **Enable**

3. **Create Service Account**:
   - Go to **APIs & Services → Credentials**
   - Click **Create Credentials → Service Account**
   - Fill in the service account details
   - Grant the role: **Cloud Vision API User**

4. **Download Credentials**:
   - Click on the created service account
   - Go to **Keys** tab
   - Click **Add Key → Create New Key**
   - Choose **JSON** format
   - Save the downloaded file as `google_credentials.json`

5. **Place Credentials**:
   ```bash
   # Move the JSON file to the project root
   mv ~/Downloads/your-service-account-key.json google_credentials.json
   ```

### Step 4: Verify Installation

```bash
# Test import of all modules
python -c "from main import process_file; print('✓ Installation successful')"
```

### Required Python Packages

The following libraries are used (install via requirements.txt):

- **pandas** - Data manipulation and Excel handling
- **numpy** - Numerical operations and matrix processing
- **opencv-python (cv2)** - Image preprocessing
- **google-cloud-vision** - OCR text extraction
- **openpyxl** - Excel file creation and parsing
- **streamlit** - Web dashboard interface
- **plotly** - Interactive charts and visualizations
- **Pillow (PIL)** - Image loading and manipulation

---

## Usage

### Method 1: Web Dashboard (Recommended)

Launch the Streamlit dashboard for interactive use:

```bash
streamlit run dashboard.py
```

The dashboard will open in your browser (default: http://localhost:8501)

**Dashboard Features**:
- 📤 **Upload Tab**: Drag and drop files for instant processing
- 📜 **History Tab**: View all past QC results
- 📈 **Analytics Tab**: Visualize quality trends
- 👁️ **Monitoring Tab**: Real-time system status
- ⚙️ **Config Tab**: View current configuration

### Method 2: Command-Line Processing

Process files directly via Python:

```python
from pathlib import Path
from main import process_file

# Process a single image
image_path = Path("input/inspection_image.jpg")
result = process_file(image_path)

print(f"Decision: {result['decision']}")
print(f"Report: {result['report_path']}")
```

### Method 3: Directory Monitoring (Batch Processing)

Place inspection files in the `input/` directory:

```bash
# Copy files to input directory
cp /path/to/inspection/*.jpg input/

# Run batch processing
python main.py
```

The system will automatically:
1. Detect all files in `input/` directory
2. Process each file sequentially
3. Move processed files to `processed/` or `failed/`
4. Generate QC reports in `output/`

### Processing with Cross-Verification

To enable Excel reference verification:

**Via Dashboard**:
1. Upload inspection image in the main file uploader
2. Upload reference Excel file in the "Optional: Excel Reference" section
3. Click "Process File"

**Via Python**:
```python
from pathlib import Path
from main import process_file

image_path = Path("input/inspection.jpg")
excel_path = Path("input/reference.xlsx")

result = process_file(image_path, excel_ref_path=excel_path)
```

### Output Files

After processing, find your results:

```
output/BATCH_20260309_143022_A1B2C3D4_Report.xlsx   # QC Report
processed/BATCH_20260309_143022_A1B2C3D4_inspection.jpg   # Processed file
logs/qc_run.log   # Processing logs
```

### Understanding Results

**Decision Categories**:
- ✅ **APPROVED**: All quality rules passed
- ❌ **REJECTED**: One or more quality rules failed
- ⚠️ **MANUAL_REVIEW_REQUIRED**: Partial data or warnings present
- 🔴 **DATA_ERROR**: Structural validation failed (bad file/format)
- 🔄 **VERIFICATION_FAILED**: Image-Excel mismatch detected

**Report Contents**:
- **Extracted Matrix**: Complete 16×7 measurement grid
- **Rule A Result**: Percentage of points above 0.8N threshold
- **Rule B Result**: Per-bar analysis of points ≤ 0.35N
- **Rule C Result**: Critical low-value point counts
- **Verification Report**: Cell-by-cell comparison (if Excel provided)
- **Metadata**: Batch ID, timestamps, file names

---

## Example Output

The generated Excel QC report typically includes:

- Extracted inspection values  
- Validation results  
- Error flags or warnings  
- Final QC status (Pass / Fail / Manual Review)

---

## Advantages

- Reduces manual inspection workload  
- Improves accuracy of QC verification  
- Handles large volumes of inspection data  
- Generates structured and easy-to-analyze reports  

---

## Future Improvements

Possible enhancements for the system include:

- Integration with deep learning based OCR models  
- Real-time monitoring dashboards  
- Cloud-based QC processing pipelines  
- Machine learning based anomaly detection for inspection data  

---

## Applications

- Solar panel manufacturing quality control  
- Automated inspection workflows  
- Renewable energy production monitoring  
- Industrial inspection automation systems  
