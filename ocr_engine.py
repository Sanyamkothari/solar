"""
OCR Engine based on Google Cloud Vision API.
Designed specifically to read data from real-world factory photos (e.g. phones taking pictures of monitors).
Uses K-Means clustering to reconstruct the 16x7 data grid despite skewed photography.
"""
import re
import logging
import numpy as np
import cv2
from typing import List, Tuple, Optional
from google.cloud import vision
from google.oauth2 import service_account
from google.oauth2 import service_account

from config import BUS_BARS, POINTS_PER_BAR, BASE_DIR, CATEGORY_MANUAL_REVIEW
from data_cleaner import DataCleaner
from validator import ValidationError

CREDENTIALS_PATH = BASE_DIR / "google_credentials.json"


class OCREngine:
    """Google Cloud Vision OCR engine for solder point table extraction."""

    _cached_client: Optional[vision.ImageAnnotatorClient] = None

    @classmethod
    def _get_vision_client(cls) -> vision.ImageAnnotatorClient:
        """Returns a cached GCP Vision client (initialises on first call)."""
        if cls._cached_client is not None:
            return cls._cached_client

        if not CREDENTIALS_PATH.exists():
            raise ValidationError(
                "Google Cloud credentials not found! \n"
                "Please place your service account JSON file at:\n"
                f"{CREDENTIALS_PATH}\n"
                "You can get this from the Google Cloud Console (APIs & Services -> Credentials)."
            )

        creds = service_account.Credentials.from_service_account_file(str(CREDENTIALS_PATH))
        cls._cached_client = vision.ImageAnnotatorClient(credentials=creds)
        return cls._cached_client

    @staticmethod
    def extract_matrix(image_np: np.ndarray, batch_manager) -> Tuple[Optional[List[List[float]]], Optional[str]]:
        """
        Runs Google Cloud Vision on a raw OpenCV image array.
        Uses K-Means clustering on Y-coordinates to perfectly construct exactly 16 rows.
        """
        client = OCREngine._get_vision_client()

        success, encoded_image = cv2.imencode('.jpg', image_np)
        if not success:
            raise ValidationError("Failed to encode image for Google Cloud Vision.")
            
        content = encoded_image.tobytes()
        image = vision.Image(content=content)
        
        try:
            response = client.document_text_detection(image=image, timeout=30)
        except Exception as e:
            raise ValidationError(f"Google Cloud Vision API request failed: {e}")

        if response.error.message:
            raise ValidationError(f"Google Cloud Vision API Error: {response.error.message}")

        # 1. Detect Table Boundaries
        # Top boundary: keywords like 'interval', 'force', '1st', '2nd'
        # Bottom boundary: keywords like 'maximum', 'minimum', 'mean'
        header_y_candidates = []
        footer_y_candidates = []
        
        for ann in response.text_annotations[1:]:
            txt_lower = ann.description.lower()
            y_center = sum(v.y for v in ann.bounding_poly.vertices) / 4.0
            
            if 'interval' in txt_lower or 'force' in txt_lower or '1st' in txt_lower or '2nd' in txt_lower:
                header_y_candidates.append(y_center)
            if 'maximum' in txt_lower or 'minimum' in txt_lower or 'mean' in txt_lower:
                footer_y_candidates.append(y_center)
        
        table_top_y = min(header_y_candidates) if header_y_candidates else 0
        
        # Use min() — the topmost footer keyword (e.g. "Maximum") marks where
        # summary rows begin.  Everything at or below that line must be excluded
        # so that K-Means only sees the 16 data rows, not the 3 summary rows.
        if footer_y_candidates:
            footer_start_y = min(footer_y_candidates)
            # Subtract a small margin (half the estimated row height) so that
            # numeric tokens on the same line as the footer keyword are excluded.
            data_span = footer_start_y - table_top_y
            row_height_est = data_span / (BUS_BARS + 1) if data_span > 0 else 0
            table_bottom_y = footer_start_y - row_height_est * 0.5
        else:
            table_bottom_y = float('inf')
        
        logging.info(f"Table Y-Boundaries: Top={table_top_y}, Bottom={table_bottom_y}")

        numeric_pattern = re.compile(r'^[\d.,OoIl]+$')
        has_digit = re.compile(r'\d')
        
        # 2. Extract words with confidence strictly within the boundaries
        words = []
        try:
            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            txt = "".join([symbol.text for symbol in word.symbols]).strip()
                            if not txt:
                                continue
                            
                            bounds = word.bounding_box.vertices
                            y_center = sum(v.y for v in bounds) / 4.0
                            x_center = sum(v.x for v in bounds) / 4.0
                            
                            if table_top_y < y_center < table_bottom_y and numeric_pattern.match(txt) and has_digit.search(txt):
                                # Calculate average symbol confidence for this word
                                confidences = [s.confidence for s in word.symbols if s.confidence > 0]
                                word_conf = sum(confidences) / len(confidences) if confidences else 1.0
                                words.append({'text': txt, 'x': x_center, 'y': y_center, 'confidence': word_conf})
        except Exception as e:
            logging.error(f"Error parsing full_text_annotation: {e}")
            raise ValidationError("Failed to parse word confidence from OCR response.")

        if len(words) < (BUS_BARS * POINTS_PER_BAR // 2):
            raise ValidationError(f"Only {len(words)} numeric tokens found in table area, expected ~112.")

        # 3. Adaptive Line Forming Algorithm
        # Sort all words top-to-bottom
        words.sort(key=lambda w: w['y'])

        # Compute adaptive Y-threshold from the actual gaps between consecutive words
        y_values = [w['y'] for w in words]
        gaps = [y_values[i+1] - y_values[i] for i in range(len(y_values) - 1) if y_values[i+1] - y_values[i] > 0]
        if gaps:
            gaps_sorted = sorted(gaps)
            median_gap = gaps_sorted[len(gaps_sorted) // 2]
            # Use 60% of the median gap as the merge threshold — tight enough
            # to avoid merging distinct rows while tolerating slight Y-jitter
            adaptive_threshold = max(median_gap * 0.6, 5)
        else:
            adaptive_threshold = 15  # safe fallback
        logging.info(f"Adaptive line threshold: {adaptive_threshold:.1f}px (median gap: {median_gap if gaps else 'N/A'})")

        lines = []
        current_line = []
        
        for w in words:
            if not current_line:
                current_line.append(w)
            else:
                avg_y = sum(item['y'] for item in current_line) / len(current_line)
                if abs(w['y'] - avg_y) < adaptive_threshold:
                    current_line.append(w)
                else:
                    lines.append(current_line)
                    current_line = [w]
        
        if current_line:
            lines.append(current_line)

        logging.info(f"Initial line grouping: {len(lines)} lines (items per line: {[len(l) for l in lines]})")

        # 3b. Split oversized lines — if a line has significantly more items than
        #     expected per row, it is likely two or more rows merged together.
        split_lines = []
        for line in lines:
            if len(line) >= POINTS_PER_BAR * 1.5:
                # Sub-sort by Y within the merged line and split using K-Means
                sub_y = np.array([w['y'] for w in line]).reshape(-1, 1)
                n_sub_rows = max(2, round(len(line) / POINTS_PER_BAR))
                from sklearn.cluster import KMeans
                km = KMeans(n_clusters=n_sub_rows, n_init=10, random_state=0).fit(sub_y)
                labels = km.labels_
                # Build sub-lines ordered by cluster centroid Y
                cluster_order = np.argsort(km.cluster_centers_.flatten())
                for cid in cluster_order:
                    sub_line = [line[i] for i in range(len(line)) if labels[i] == cid]
                    if sub_line:
                        split_lines.append(sub_line)
                logging.info(f"Split oversized line ({len(line)} items) into {n_sub_rows} sub-rows.")
            else:
                split_lines.append(line)
        lines = split_lines

        # 4. Extract data rows
        # A valid data row usually has ~7+ numeric items. We filter out header/noise lines.
        valid_data_lines = [line for line in lines if len(line) >= POINTS_PER_BAR - 1]
        
        if len(valid_data_lines) < BUS_BARS:
             logging.warning(f"Found {len(valid_data_lines)} valid rows, expected {BUS_BARS}.")
             # Include shorter lines as well if they have at least 4 items
             valid_data_lines = [line for line in lines if len(line) >= 4]
             if len(valid_data_lines) < BUS_BARS:
                 logging.warning(f"Even with relaxed filter: {len(valid_data_lines)} rows. Using all available.")

        # Sort the rows top-to-bottom
        valid_data_lines.sort(key=lambda line: sum(w['y'] for w in line) / len(line))
        
        # Cap at BUS_BARS if we found more
        if len(valid_data_lines) > BUS_BARS:
            valid_data_lines = valid_data_lines[:BUS_BARS]

        matrix = []
        for line in valid_data_lines:
            line.sort(key=lambda w: w['x']) # Sort horizontally
            
            row_items = [{'val': w['text'], 'confidence': w['confidence']} for w in line]
            
            # The grid contains 7 data points. The 8th column is "max avg force" (which we ignore).
            # Numeric IDs on the left (e.g., '1028', '1') are noise. 
            if len(row_items) >= POINTS_PER_BAR + 1:
                # Take the last 8 items, then grab the first 7
                data_cols = row_items[-(POINTS_PER_BAR + 1):]
                matrix.append(data_cols[:POINTS_PER_BAR])
            elif len(row_items) == POINTS_PER_BAR:
                matrix.append(row_items)
            else:
                padding = [{'val': "0.0", 'confidence': 0.0}] * (POINTS_PER_BAR - len(row_items))
                matrix.append(row_items + padding)

        # Compute average symbol confidence from the full-text annotation (page->block->paragraph->word->symbol)
        confidences = []
        try:
            for page in response.full_text_annotation.pages:
                for block in page.blocks:
                    for paragraph in block.paragraphs:
                        for word in paragraph.words:
                            for symbol in word.symbols:
                                if symbol.confidence > 0:
                                    confidences.append(symbol.confidence)
        except Exception:
            pass  # GCP may not always return confidence; fall back gracefully

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        batch_manager.set_metadata("ocr_avg_confidence", round(avg_confidence, 4))
        logging.info(f"OCR average symbol confidence: {avg_confidence:.4f} ({len(confidences)} symbols)")

        # Clean to floats
        clean_matrix = DataCleaner.clean_matrix(matrix)
        
        return clean_matrix, None
