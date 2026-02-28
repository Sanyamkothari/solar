"""
Image Processor for Google Cloud Vision Pipeline.
Cloud Vision works best on UNPROCESSED images, as their deep learning models 
expect natural lighting, shadows, and color to perform optimal document text detection.
We only apply structural transformations like cropping.
"""
import cv2
import numpy as np
import logging

class ImageProcessor:
    @staticmethod
    def preprocess_image(filepath: str) -> np.ndarray:
        """
        Loads the image and applies structural cropping for factory monitor photos.
        Avoids aggressive pixel filtering (denoise, binarize, CLAHE) as Cloud Vision handles that internally.
        """
        img = cv2.imread(filepath)
        if img is None:
            raise ValueError(f"Could not read image from {filepath}")
        
        h, w = img.shape[:2]
        
        # Determine if it's a photo or a screenshot based on aspect ratio/resolution
        # Factory photos are usually typical phone resolutions (e.g. 4:3 or 16:9)
        # We crop to the data table area (bottom ~55%) to remove toolbars, headers, and background walls
        # This helps GCP focus its bounding box clustering on just the numeric grid
        
        # Safe crop: bottom 60% of image, leaving a bit of margin
        cropped = img[int(h * 0.40):int(h * 0.95), int(w * 0.05):int(w * 0.97)]
        
        logging.info(f"Image cropped from {img.shape} to {cropped.shape} for Cloud Vision.")
        
        return cropped

    @staticmethod
    def preprocess_clean_image(filepath: str) -> np.ndarray:
        """
        Pass-through for clean/direct screenshots.
        """
        img = cv2.imread(filepath)
        if img is None:
            raise ValueError(f"Could not read image from {filepath}")
        return img
