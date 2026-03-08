import os
from pathlib import Path
from image_processor import ImageProcessor
from ocr_engine import OCREngine
import cv2

class MockBatchManager:
    def __init__(self):
        self.metadata = {}
    def set_metadata(self, key, value):
        self.metadata[key] = value

def test_image(img_path):
    with open("test_ocr_result.txt", "w") as f:
        f.write(f"Testing {img_path}\n")
        try:
            img_np = ImageProcessor.preprocess_image(img_path)
            cv2.imwrite("debug_preprocessed.jpg", img_np)
            f.write("Image preprocessed and saved to debug_preprocessed.jpg\n")
            
            manager = MockBatchManager()
            matrix, cat = OCREngine.extract_matrix(img_np, manager)
            
            f.write("\n--- EXTRACTED MATRIX ---\n")
            if matrix:
                for i, row in enumerate(matrix):
                    f.write(f"Row {i+1} ({len(row)}): {row}\n")
            else:
                f.write("No matrix returned.\n")
                
            f.write(f"\nCategory: {cat}\n")
            f.write(f"Metadata: {manager.metadata}\n")
        except Exception as e:
            f.write(f"Error: {e}\n")

if __name__ == "__main__":
    test_image(r"c:\Users\sanya\OneDrive\Desktop\O2\QC_Automation\failed\BATCH_20260305_172030_7206AD38_WhatsApp Image 2026-03-05 at 5.20.05 PM.jpeg")
