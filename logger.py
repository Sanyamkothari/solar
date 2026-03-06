"""
Logger configuration for the Manufacturing Quality Control Automation System.
Sets up timed-rotating file logging to trace execution steps, success/failures, and decisions.
"""
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from config import LOGS_DIR, LOG_MAX_BYTES, LOG_BACKUP_COUNT

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

    # File Handler — rotates at midnight, keeps LOG_BACKUP_COUNT days of history
    log_file = LOGS_DIR / "qc_run.log"
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8"
    )
    file_handler.suffix = "%Y%m%d"  # rotated files: qc_run.log.20260305
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Stream Handler (Stdout)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger

logger = setup_logger()
