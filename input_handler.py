"""
Input Handler for folder monitoring.
Scans the /input folder, routes files by extension to OCR or Excel parsers.
Moves files safely to /processed or /failed avoiding re-processing.
"""
from pathlib import Path
import shutil
import re
import time
from typing import Tuple, List, Optional
from config import INPUT_DIR, PROCESSED_DIR, FAILED_DIR, CATEGORY_DATA_ERROR, MAX_FILE_SIZE_BYTES
from logger import logger
from excel_parser import ExcelParser
from validator import ValidationError
from batch_manager import BatchManager

class InputHandler:
    SUPPORTED_EXTENSIONS = {'.xlsx': 'EXCEL', '.xls': 'EXCEL', '.png': 'IMAGE', '.jpg': 'IMAGE', '.jpeg': 'IMAGE'}

    @staticmethod
    def get_pending_files() -> List[Path]:
        """Returns a list of files waiting in the input directory, sorted by modification time (FIFO)."""
        files = [f for f in INPUT_DIR.iterdir() if f.is_file()]
        files.sort(key=lambda f: f.stat().st_mtime)
        return files

    @staticmethod
    def extract_excel_reference(filepath: Path) -> Optional[List[List[float]]]:
        """
        Extracts the 16×7 matrix from a user-provided Excel reference file.
        Used for cross-verification against OCR-extracted data.
        Returns None if extraction fails.
        """
        ext = filepath.suffix.lower()
        if ext not in ('.xlsx', '.xls'):
            logger.error(f"Reference file must be .xlsx or .xls, got: {ext}")
            return None
        try:
            matrix = ExcelParser.extract_matrix(str(filepath))
            return matrix
        except (ValidationError, Exception) as e:
            logger.error(f"Failed to extract reference Excel: {e}")
            return None

    @staticmethod
    def route_file(filepath: Path, batch_manager: BatchManager) -> Tuple[Optional[List[List[float]]], Optional[str]]:
        """
        Determines file type and routes to appropriate extraction engine.
        Returns the Extracted Matrix and a Category override (e.g. MANUAL_REVIEW_REQUIRED, DATA_ERROR)
        """
        ext = filepath.suffix.lower()
        if ext not in InputHandler.SUPPORTED_EXTENSIONS:
            logger.error(f"Unsupported file format: {ext} for {filepath.name}")
            return None, CATEGORY_DATA_ERROR

        # Reject oversized files before spending resources
        file_size = filepath.stat().st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            logger.error(f"File {filepath.name} exceeds size limit ({file_size} bytes > {MAX_FILE_SIZE_BYTES} bytes)")
            return None, CATEGORY_DATA_ERROR

        file_type = InputHandler.SUPPORTED_EXTENSIONS[ext]
        matrix = None
        category_override = None

        try:
            if file_type == 'EXCEL':
                logger.info("Routing to Excel Parser...")
                matrix = ExcelParser.extract_matrix(str(filepath))
            elif file_type == 'IMAGE':
                logger.info("Routing to OpenCV & OCR Engine...")
                # Lazy loading to avoid OCR instantiation if just handling Excel
                from image_processor import ImageProcessor
                from ocr_engine import OCREngine
                
                img_proc = ImageProcessor.preprocess_image(str(filepath))
                ocr_eng = OCREngine()
                matrix, ocr_cat = ocr_eng.extract_matrix(img_proc, batch_manager)
                if ocr_cat:
                    category_override = ocr_cat
                    
        except ValidationError as ve:
             logger.error(f"Validation Error during extraction: {ve}")
             return None, CATEGORY_DATA_ERROR
        except Exception as e:
             logger.error(f"Unexpected extraction error for {filepath.name}: {e}")
             return None, CATEGORY_DATA_ERROR
             
        return matrix, category_override

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Strip directory separators and dangerous characters from a filename."""
        name = Path(name).name  # strip any directory components
        name = re.sub(r'[^\w.\-()]', '_', name)  # keep only safe chars
        return name

    @staticmethod
    def move_file(filepath: Path, success: bool, batch_id: str):
        """Moves original file to the processed or failed directory."""
        target_dir = PROCESSED_DIR if success else FAILED_DIR
        safe_name = f"{batch_id}_{InputHandler._sanitize_filename(filepath.name)}"
        target_path = target_dir / safe_name
        # Ensure the resolved path stays inside the target directory
        if not target_path.resolve().is_relative_to(target_dir.resolve()):
            logger.error(f"Path traversal blocked for filename: {filepath.name}")
            return
        
        try:
            shutil.move(str(filepath), str(target_path))
            logger.info(f"Moved {filepath.name} to {target_dir.name}/{safe_name}")
        except Exception as e:
             logger.error(f"Failed to move file {filepath.name} to {target_dir.name}: {e}")
