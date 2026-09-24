"""
FinePrint — OCR Module

Phone photo preprocessing + Tesseract OCR.
Handles poor lighting, angle distortion, and low quality images
that are the common real-world input.
"""

from __future__ import annotations

import io
import os
import logging

import cv2
import numpy as np
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)

# Configure Tesseract path from env
TESSERACT_CMD = os.getenv(
    "TESSERACT_CMD",
    r"D:\Extra application\Tesseract-OCR\tesseract.exe"
)
if os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


def ocr_image(content: bytes) -> str:
    """
    Full OCR pipeline for a phone photo or scanned image.

    Steps:
    1. Decode image
    2. Resize if too small
    3. Convert to grayscale
    4. Deskew
    5. Adaptive threshold
    6. Denoise
    7. Run Tesseract

    Args:
        content: Raw image bytes

    Returns:
        Extracted text string
    """
    # Decode image
    img_array = np.frombuffer(content, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Could not decode image")

    # Preprocess
    processed = _preprocess_image(img)

    # Convert back to PIL for Tesseract
    pil_img = Image.fromarray(processed)

    # Run Tesseract with optimal settings for document OCR
    text = pytesseract.image_to_string(
        pil_img,
        lang="eng",
        config="--oem 3 --psm 6"
    )

    return text.strip()


def ocr_page_image(content: bytes) -> str:
    """
    OCR a rendered page image (from PDF fallback).
    Lighter preprocessing since the image is already clean.
    """
    img_array = np.frombuffer(content, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if img is None:
        return ""

    # Lighter preprocessing for rendered pages
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Simple threshold
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    pil_img = Image.fromarray(binary)
    text = pytesseract.image_to_string(
        pil_img,
        lang="eng",
        config="--oem 3 --psm 6"
    )

    return text.strip()


def _preprocess_image(img: np.ndarray) -> np.ndarray:
    """
    Full preprocessing pipeline for phone photos.

    Handles:
    - Poor lighting
    - Angle distortion (deskew)
    - Low contrast
    - Noise
    """
    # Step 1: Resize if too small (minimum 1000px width for good OCR)
    h, w = img.shape[:2]
    if w < 1000:
        scale = 1000 / w
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # Step 2: Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Step 3: Deskew
    gray = _deskew(gray)

    # Step 4: Adaptive threshold for handling uneven lighting
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=21,
        C=10
    )

    # Step 5: Denoise
    denoised = cv2.fastNlMeansDenoising(binary, h=10)

    # Step 6: Morphological cleanup to remove small artifacts
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    cleaned = cv2.morphologyEx(denoised, cv2.MORPH_CLOSE, kernel)

    return cleaned


def _deskew(gray: np.ndarray) -> np.ndarray:
    """
    Correct rotation/skew in a document image.
    Uses Hough line transform to detect the dominant angle.
    """
    try:
        # Edge detection
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Detect lines
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180,
            threshold=100,
            minLineLength=100,
            maxLineGap=10
        )

        if lines is None or len(lines) == 0:
            return gray

        # Calculate angles
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.arctan2(y2 - y1, x2 - x1) * 180.0 / np.pi
            # Only consider near-horizontal lines (within 30 degrees)
            if abs(angle) < 30:
                angles.append(angle)

        if not angles:
            return gray

        # Median angle for robustness
        median_angle = np.median(angles)

        # Only correct if skew is significant but not too extreme
        if abs(median_angle) < 0.5 or abs(median_angle) > 15:
            return gray

        # Rotate to correct skew
        h, w = gray.shape
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(
            gray, rotation_matrix, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )

        logger.info(f"Deskewed image by {median_angle:.2f} degrees")
        return rotated

    except Exception as e:
        logger.warning(f"Deskew failed: {e}, using original image")
        return gray
