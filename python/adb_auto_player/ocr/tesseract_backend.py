"""Tesseract OCR backend implementation."""

import os
import platform
from typing import Any

import cv2
import numpy as np
import pytesseract
from adb_auto_player.models.geometry.box import Box
from adb_auto_player.models.ocr.ocr_result import OCRResult
from PIL import Image
from pytesseract import TesseractNotFoundError

from .. import ConfigLoader
from .ocr_backend import OCRBackend

_NUM_COLORS_IN_RGB = 3


class TesseractBackend(OCRBackend):
    """Tesseract OCR backend implementation."""

    def __init__(self, config: str = "--oem 3 --psm 6", lang: str = "eng"):
        """Initialize Tesseract backend.

        Args:
            config: Tesseract configuration string
            lang: Language code for OCR (e.g., 'eng', 'chi_sim', 'jpn')
        """
        self.config = config
        self.lang = lang

        try:
            pytesseract.get_tesseract_version()
        except TesseractNotFoundError as e:
            if platform.system() != "Windows":
                raise RuntimeError(
                    f"Tesseract not found or not properly configured: {e}"
                )

            fallback_path = (
                ConfigLoader().binaries_dir / "windows" / "tesseract" / "tesseract.exe"
            )

            if not os.path.isfile(fallback_path):
                raise RuntimeError(
                    "Tesseract not found in system PATH "
                    f"and fallback binary not found at {fallback_path}"
                )

            # Use the fallback tesseract executable
            pytesseract.pytesseract.tesseract_cmd = fallback_path

            try:
                pytesseract.get_tesseract_version()
            except Exception as e2:
                raise RuntimeError(f"Tesseract fallback also failed: {e2}")

        except Exception as e:
            raise e

    def extract_text(self, image: np.ndarray, **kwargs) -> str:
        """Extract all text from an image as a single string.

        Args:
            image: Input image as numpy array
            **kwargs: Additional arguments (config, lang can override defaults)

        Returns:
            str: Extracted text
        """
        config = kwargs.get("config", self.config)
        lang = kwargs.get("lang", self.lang)

        # Convert numpy array to PIL Image
        if len(image.shape) == _NUM_COLORS_IN_RGB:
            # Convert BGR to RGB if needed
            if image.shape[2] == _NUM_COLORS_IN_RGB:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                image_rgb = image
            pil_image = Image.fromarray(image_rgb)
        else:
            # Grayscale image
            pil_image = Image.fromarray(image)

        # Extract text
        text = pytesseract.image_to_string(pil_image, config=config, lang=lang).strip()

        return text

    def detect_text_with_boxes(self, image: np.ndarray, **kwargs) -> list[OCRResult]:
        """Detect text and return results with bounding boxes.

        Args:
            image: Input image as numpy array
            **kwargs: Additional arguments (config, lang, min_confidence)

        Returns:
            list[OCRResult]: List of OCR results with bounding boxes
        """
        config = kwargs.get("config", self.config)
        lang = kwargs.get("lang", self.lang)
        min_confidence = kwargs.get("min_confidence", 0.0)

        # Convert numpy array to PIL Image
        if len(image.shape) == _NUM_COLORS_IN_RGB:
            # Convert BGR to RGB if needed
            if image.shape[2] == _NUM_COLORS_IN_RGB:
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            else:
                image_rgb = image
            pil_image = Image.fromarray(image_rgb)
        else:
            # Grayscale image
            pil_image = Image.fromarray(image)

        # Get detailed data including bounding boxes
        data = pytesseract.image_to_data(
            pil_image, config=config, lang=lang, output_type=pytesseract.Output.DICT
        )

        results = []
        n_boxes = len(data["text"])

        for i in range(n_boxes):
            # Skip empty text and low confidence results
            text = data["text"][i].strip()
            confidence = float(data["conf"][i])
            # Convert confidence from 0-100 to 0-1 scale
            confidence_normalized = confidence / 100.0

            if not text or confidence_normalized < min_confidence:
                continue

            # Extract bounding box coordinates
            x = int(data["left"][i])
            y = int(data["top"][i])
            width = int(data["width"][i])
            height = int(data["height"][i])

            try:
                box = Box(x=x, y=y, width=width, height=height)

                result = OCRResult(text=text, confidence=confidence_normalized, box=box)
                results.append(result)

            except ValueError:
                # Skip invalid boxes
                continue

        return results

    def get_backend_info(self) -> dict[str, Any]:
        """Get information about the backend.

        Returns:
            dict: Backend information
        """
        try:
            version = pytesseract.get_tesseract_version()
            version_str = ".".join(map(str, version))
        except Exception:
            version_str = "Unknown"

        return {
            "name": "Tesseract",
            "version": version_str,
            "config": self.config,
            "language": self.lang,
            "supported_languages": self._get_supported_languages(),
        }

    def _get_supported_languages(self) -> list[str]:
        """Get list of supported languages.

        Returns:
            list[str]: List of supported language codes
        """
        try:
            langs = pytesseract.get_languages(config="")
            return sorted(langs)
        except Exception:
            return ["eng"]  # Default fallback

    def preprocess_image(self, image: np.ndarray, **kwargs) -> np.ndarray:
        """Preprocess image for better OCR results.

        Args:
            image: Input image as numpy array
            **kwargs: Preprocessing options

        Returns:
            np.ndarray: Preprocessed image
        """
        # Convert to grayscale if needed
        if len(image.shape) == _NUM_COLORS_IN_RGB:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Apply preprocessing based on kwargs
        if kwargs.get("denoise", False):
            gray = cv2.fastNlMeansDenoising(gray)

        if kwargs.get("threshold", False):
            _, gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        if kwargs.get("scale_factor", 1.0) != 1.0:
            scale = kwargs["scale_factor"]
            height, width = gray.shape[:2]
            new_width = int(width * scale)
            new_height = int(height * scale)
            gray = cv2.resize(
                gray, (new_width, new_height), interpolation=cv2.INTER_CUBIC
            )

        return gray
