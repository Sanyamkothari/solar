"""
Image Processor for Google Cloud Vision Pipeline.
Applies light preprocessing to improve OCR accuracy on real-world factory photos
(phone cameras photographing monitors) while keeping the image natural enough
for Cloud Vision's deep learning models.
"""
import cv2
import numpy as np
import logging

from config import (
    IMG_CROP_TOP, IMG_CROP_BOTTOM, IMG_CROP_LEFT, IMG_CROP_RIGHT,
    IMG_DESKEW_MIN_ANGLE, IMG_DESKEW_MAX_ANGLE, IMG_PERSPECTIVE_MIN_AREA,
    IMG_DENOISE_H, IMG_CLAHE_CLIP, IMG_CLAHE_GRID,
    IMG_SHARPEN_WEIGHT, IMG_SHARPEN_BLUR_WEIGHT,
)


class ImageProcessor:

    # ── Phone photo of monitor ──────────────────────────────────────────
    @staticmethod
    def preprocess_image(filepath: str) -> np.ndarray:
        """
        Full preprocessing pipeline for phone photos of factory monitors:
        1. Load & crop to data table region
        2. Perspective / deskew correction
        3. Light denoising
        4. Contrast enhancement (CLAHE)
        5. Mild sharpening
        """
        img = cv2.imread(filepath)
        if img is None:
            raise ValueError(f"Could not read image from {filepath}")

        h, w = img.shape[:2]

        # 1. Crop to the data table area (bottom ~60%) to remove toolbars & background
        cropped = img[int(h * IMG_CROP_TOP):int(h * IMG_CROP_BOTTOM), int(w * IMG_CROP_LEFT):int(w * IMG_CROP_RIGHT)]
        logging.info(f"Cropped from {img.shape} to {cropped.shape}")

        # 2. Deskew — straighten rotated photos
        cropped = ImageProcessor._deskew(cropped)

        # 3. Perspective correction — flatten trapezoidal distortion from angled shots
        cropped = ImageProcessor._correct_perspective(cropped)

        # 4. Light denoising (preserve edges for digits)
        cropped = cv2.fastNlMeansDenoisingColored(cropped, None, h=IMG_DENOISE_H, hColor=IMG_DENOISE_H,
                                                   templateWindowSize=7, searchWindowSize=21)

        # 5. CLAHE contrast enhancement on the L channel (keeps colours natural)
        cropped = ImageProcessor._enhance_contrast(cropped)

        # 6. Mild sharpen to crisp up digit edges
        cropped = ImageProcessor._sharpen(cropped)

        logging.info(f"Preprocessing complete. Final size: {cropped.shape}")
        return cropped

    # ── Direct screenshot ───────────────────────────────────────────────
    @staticmethod
    def preprocess_clean_image(filepath: str) -> np.ndarray:
        """
        Light preprocessing for clean screenshots — no geometric correction needed,
        but contrast + sharpen still help OCR on low-quality screen grabs.
        """
        img = cv2.imread(filepath)
        if img is None:
            raise ValueError(f"Could not read image from {filepath}")

        img = ImageProcessor._enhance_contrast(img)
        img = ImageProcessor._sharpen(img)
        logging.info(f"Screenshot preprocessed. Size: {img.shape}")
        return img

    # ── Internal helpers ────────────────────────────────────────────────
    @staticmethod
    def _deskew(img: np.ndarray) -> np.ndarray:
        """Detect dominant text-line angle via Hough lines and rotate to level."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                                minLineLength=img.shape[1] // 6, maxLineGap=10)
        if lines is None:
            return img

        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            dx = x2 - x1
            dy = y2 - y1
            if abs(dx) < 1:
                continue
            angle = np.degrees(np.arctan2(dy, dx))
            # Only consider near-horizontal lines (table rows)
            if abs(angle) < IMG_DESKEW_MAX_ANGLE:
                angles.append(angle)

        if not angles:
            return img

        median_angle = float(np.median(angles))
        # Skip rotation if the skew is negligible
        if abs(median_angle) < IMG_DESKEW_MIN_ANGLE:
            logging.info(f"Deskew: angle {median_angle:.2f}° — negligible, skipped.")
            return img

        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        rot_mat = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(img, rot_mat, (w, h),
                                 flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_REPLICATE)
        logging.info(f"Deskew: rotated by {median_angle:.2f}°")
        return rotated

    @staticmethod
    def _correct_perspective(img: np.ndarray) -> np.ndarray:
        """
        Attempt to detect a rectangular table region and warp it to a flat rectangle.
        Falls back gracefully if no strong rectangle is found.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 30, 120)

        # Dilate to close gaps in table borders
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        edges = cv2.dilate(edges, kernel, iterations=2)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return img

        # Find the largest quadrilateral contour
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        target_quad = None
        img_area = img.shape[0] * img.shape[1]

        for cnt in contours[:5]:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
            area = cv2.contourArea(approx)
            # Must be a quad covering at least 30% of the cropped image
            if len(approx) == 4 and area > img_area * IMG_PERSPECTIVE_MIN_AREA:
                target_quad = approx.reshape(4, 2).astype(np.float32)
                break

        if target_quad is None:
            logging.info("Perspective: no dominant quad found — skipped.")
            return img

        # Order points: top-left, top-right, bottom-right, bottom-left
        rect = ImageProcessor._order_points(target_quad)
        tl, tr, br, bl = rect

        width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
        height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))

        dst = np.array([[0, 0], [width - 1, 0],
                        [width - 1, height - 1], [0, height - 1]], dtype=np.float32)

        matrix = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img, matrix, (width, height),
                                     flags=cv2.INTER_LINEAR,
                                     borderMode=cv2.BORDER_REPLICATE)
        logging.info(f"Perspective: warped to {warped.shape}")
        return warped

    @staticmethod
    def _order_points(pts: np.ndarray) -> np.ndarray:
        """Order 4 points as: top-left, top-right, bottom-right, bottom-left."""
        rect = np.zeros((4, 2), dtype=np.float32)
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]   # top-left has smallest sum
        rect[2] = pts[np.argmax(s)]   # bottom-right has largest sum
        d = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(d)]   # top-right has smallest difference
        rect[3] = pts[np.argmax(d)]   # bottom-left has largest difference
        return rect

    @staticmethod
    def _enhance_contrast(img: np.ndarray) -> np.ndarray:
        """Apply CLAHE on the L channel of LAB colour space."""
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=IMG_CLAHE_CLIP, tileGridSize=IMG_CLAHE_GRID)
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    @staticmethod
    def _sharpen(img: np.ndarray) -> np.ndarray:
        """Mild unsharp-mask style sharpening to crisp digit edges."""
        blurred = cv2.GaussianBlur(img, (0, 0), sigmaX=2)
        return cv2.addWeighted(img, IMG_SHARPEN_WEIGHT, blurred, IMG_SHARPEN_BLUR_WEIGHT, 0)
