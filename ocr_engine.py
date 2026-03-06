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
from sklearn.cluster import KMeans

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
        
        # 2. Extract valid words strictly within the boundaries
        words = []
        for ann in response.text_annotations[1:]: 
            txt = ann.description.strip()
            bounds = ann.bounding_poly.vertices
            y_center = sum(v.y for v in bounds) / 4.0
            x_center = sum(v.x for v in bounds) / 4.0
            
            if table_top_y < y_center < table_bottom_y and numeric_pattern.match(txt) and has_digit.search(txt):
                words.append({'text': txt, 'x': x_center, 'y': y_center})

        if len(words) < (BUS_BARS * POINTS_PER_BAR // 2):
            raise ValidationError(f"Only {len(words)} numeric tokens found in table area, expected ~112.")

        # 3. Use K-Means to cluster exactly 16 rows based on Y-coordinates
        y_coords = np.array([w['y'] for w in words]).reshape(-1, 1)
        
        try:
            kmeans = KMeans(n_clusters=BUS_BARS, random_state=42, n_init=10).fit(y_coords)
        except ValueError as e:
            raise ValidationError(f"K-Means clustering failed: {e}")

        centers = kmeans.cluster_centers_.flatten()
        labels = kmeans.labels_

        clusters = {i: [] for i in range(BUS_BARS)}
        for i, w in enumerate(words):
            clusters[labels[i]].append(w)

        sorted_cluster_ids = np.argsort(centers)

        matrix = []
        for cid in sorted_cluster_ids:
            cluster = clusters[cid]
            cluster.sort(key=lambda w: w['x'])
            
            row_vals = [w['text'] for w in cluster]
            
            # 4. Extract columns intelligently
            # The grid contains 7 data points. The 8th column is "max avg force" (which we ignore).
            # Numeric IDs on the left (e.g., '1028', '1') are noise. 
            # Because the data + max avg are strictly the right-most columns, we take the last 8 items, 
            # and then take the first 7 of those 8.
            
            if len(row_vals) >= POINTS_PER_BAR + 1:
                # 8 or more values: Take the last 8, then grab the first 7 (dropping max avg force)
                data_cols = row_vals[-(POINTS_PER_BAR + 1):]
                matrix.append(data_cols[:POINTS_PER_BAR])
            elif len(row_vals) == POINTS_PER_BAR:
                # Exactly 7 values. Assume missing max avg force.
                matrix.append(row_vals)
            else:
                padding = ["0.0"] * (POINTS_PER_BAR - len(row_vals))
                matrix.append(row_vals + padding)

        logging.info(f"GCP Vision extracted {len(words)} tokens into {BUS_BARS}x{POINTS_PER_BAR} matrix.")

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
