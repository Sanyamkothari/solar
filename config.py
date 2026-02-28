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

# Data Structure Assumptions
TOTAL_POINTS = 112
BUS_BARS = 16
POINTS_PER_BAR = 7

# Quality Criteria Thresholds
RULE_A_THRESHOLD = 0.8
RULE_A_PERCENTAGE = 0.75
MIN_POINTS_RULE_A = int(TOTAL_POINTS * RULE_A_PERCENTAGE)

RULE_B_THRESHOLD = 0.35
MAX_RULE_B_PER_BAR = 2

RULE_C_THRESHOLD = 0.1
MAX_RULE_C_TOTAL = 8
MAX_RULE_C_PER_BAR = 1

# OCR Settings
MIN_OCR_CONFIDENCE = 0.85

# Categories
CATEGORY_APPROVED = "APPROVED"
CATEGORY_REJECTED = "REJECTED"
CATEGORY_MANUAL_REVIEW = "MANUAL_REVIEW_REQUIRED"
CATEGORY_DATA_ERROR = "DATA_ERROR"
