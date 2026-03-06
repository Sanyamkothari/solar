"""
Configuration constants for the Manufacturing Quality Control Automation System.
Defines processing rules, directories, and thresholds.
"""
import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
PROCESSED_DIR = BASE_DIR / "processed"
FAILED_DIR = BASE_DIR / "failed"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
for d in [INPUT_DIR, PROCESSED_DIR, FAILED_DIR, OUTPUT_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Data Structure Assumptions (from solder-point test equipment: 16 bus bars × 7 measurement points each)
BUS_BARS = 16
POINTS_PER_BAR = 7
TOTAL_POINTS = BUS_BARS * POINTS_PER_BAR  # 112
assert TOTAL_POINTS == BUS_BARS * POINTS_PER_BAR, "TOTAL_POINTS must equal BUS_BARS × POINTS_PER_BAR"

# Quality Criteria Thresholds (per manufacturing QC spec)
RULE_A_THRESHOLD = 0.8       # Minimum acceptable peel force (N)
RULE_A_PERCENTAGE = 0.75     # At least 75% of all points must exceed RULE_A_THRESHOLD
MIN_POINTS_RULE_A = int(TOTAL_POINTS * RULE_A_PERCENTAGE)  # 84 points

RULE_B_THRESHOLD = 0.35      # Low-force warning threshold (N)
MAX_RULE_B_PER_BAR = 2       # Max points ≤ 0.35 allowed per bus bar before rejection

RULE_C_THRESHOLD = 0.1       # Critical low-force threshold (N)
MAX_RULE_C_TOTAL = 8         # Max total points ≤ 0.1 across all bars
MAX_RULE_C_PER_BAR = 1       # Max points ≤ 0.1 allowed per single bar

# OCR Settings
MIN_OCR_CONFIDENCE = 0.85

# Data bounds — any cleaned value outside this range is flagged as OCR noise
DATA_VALUE_MIN = 0.0
DATA_VALUE_MAX = 10.0  # solder peel force rarely exceeds 10 N

# File size limit (bytes) — reject files larger than this before processing
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

# Image preprocessing thresholds (used by image_processor.py)
IMG_CROP_TOP = 0.40
IMG_CROP_BOTTOM = 0.95
IMG_CROP_LEFT = 0.05
IMG_CROP_RIGHT = 0.97
IMG_DESKEW_MIN_ANGLE = 0.3       # degrees — skip rotation below this
IMG_DESKEW_MAX_ANGLE = 15.0      # degrees — ignore lines steeper than this
IMG_PERSPECTIVE_MIN_AREA = 0.3   # fraction of image area for quad detection
IMG_DENOISE_H = 6
IMG_CLAHE_CLIP = 2.0
IMG_CLAHE_GRID = (8, 8)
IMG_SHARPEN_WEIGHT = 1.3
IMG_SHARPEN_BLUR_WEIGHT = -0.3

# Logging
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

# Cross-Verification Settings (Image vs Excel comparison)
VERIFY_TOLERANCE = 0.05       # Max allowed absolute difference per cell before flagging mismatch
VERIFY_MATCH_THRESHOLD = 0.95 # Minimum fraction of cells that must match for verification to PASS (95%)

# Categories
CATEGORY_APPROVED = "APPROVED"
CATEGORY_REJECTED = "REJECTED"
CATEGORY_MANUAL_REVIEW = "MANUAL_REVIEW_REQUIRED"
CATEGORY_DATA_ERROR = "DATA_ERROR"
CATEGORY_VERIFICATION_FAILED = "VERIFICATION_FAILED"
