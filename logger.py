"""
Logger configuration for the Manufacturing Quality Control Automation System.
Sets up rolling file logging to trace execution steps, success/failures, and decisions.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime
from config import LOGS_DIR

def setup_logger():
    # Create logger
    logger = logging.getLogger("QC_Automation_Logger")
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Log format
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File Handler (Rolling)
    log_file = LOGS_DIR / f"qc_run_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024, # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Stream Handler (Stdout)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger

logger = setup_logger()
