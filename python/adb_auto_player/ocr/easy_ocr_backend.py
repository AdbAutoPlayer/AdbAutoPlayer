"""EasyOCR backend implementation."""

from typing import Any

import easyocr
import numpy as np
from adb_auto_player.models.geometry.box import Box
from adb_auto_player.models.ocr.ocr_result import OCRResult

from .ocr_backend import OCRBackend


class EasyOCRBackend(OCRBackend):
    """EasyOCR backend implementation."""

    def __init__(self, languages: list[str] | None = None, gpu: bool = False):
        """Initialize EasyOCR backend.

        Args:
            languages: List of language codes (e.g., ['en', 'ch_sim', 'ja'])
            gpu: Whether to use GPU acceleration if available
        """
        if languages is None:
            languages = ["en"]

        self.languages = languages
        self.gpu = gpu

        # Initialize EasyOCR reader
        try:
            self.reader = easyocr.Reader(languages, gpu=gpu)
        except Exception as e:
            # Fallback to CPU if GPU initialization fails
            if gpu:
                try:
                    self.reader = easyocr.Reader(languages, gpu=False)
                    self.gpu = False
                except Exception as e2:
                    raise RuntimeError(f"Failed to initialize EasyOCR: {e2}")
            else:
                raise RuntimeError(f"Failed to initialize EasyOCR: {e}")

    def extract_text(self, image: np.ndarray, **kwargs) -> str:
        """Extract all text from an image as a single string.

        Args:
            image: Input image as numpy array
            **kwargs: Additional arguments for EasyOCR

        Returns:
            str: Extracted text
        """
        # Set default parameters
        paragraph = kwargs.get("paragraph", False)
        detail = kwargs.get("detail", 0)  # 0 = text only

        # Extract text using EasyOCR
        try:
            results = self.reader.readtext(
                image, paragraph=paragraph, detail=detail, **kwargs
            )

            # If detail=0, results is a list of strings
            if detail == 0:
                return " ".join(results)

            # If detail=1, results contain bounding boxes and confidence
            # Extract only the text parts
            texts = []
            for result in results:
                min_items = 2
                if isinstance(result, (list | tuple)) and len(result) >= min_items:
                    # Format: [bbox, text, confidence] or [bbox, text]
                    texts.append(str(result[1]))
                else:
                    texts.append(str(result))

            return " ".join(texts)

        except Exception as e:
            raise RuntimeError(f"EasyOCR text extraction failed: {e}")

    def detect_text_with_boxes(self, image: np.ndarray, **kwargs) -> list[OCRResult]:
        """Detect text and return results with bounding boxes.

        Args:
            image: Input image as numpy array
            **kwargs: Additional arguments (min_confidence, etc.)

        Returns:
            list[OCRResult]: List of OCR results with bounding boxes
        """
        min_confidence = kwargs.get("min_confidence", 0.0)
        paragraph = kwargs.get("paragraph", False)

        # Remove our custom kwargs before passing to EasyOCR
        easyocr_kwargs = {
            k: v for k, v in kwargs.items() if k not in ["min_confidence"]
        }

        try:
            # Get detailed results with bounding boxes
            raw_results = self.reader.readtext(
                image,
                paragraph=paragraph,
                detail=1,  # Include bounding boxes and confidence
                **easyocr_kwargs,
            )

            results = []

            for raw_result in raw_results:
                try:
                    # EasyOCR returns: [bbox_points, text, confidence]
                    bbox_points, text, confidence = raw_result

                    # Skip low confidence results
                    if confidence < min_confidence:
                        continue

                    # Skip empty text
                    text = str(text).strip()
                    if not text:
                        continue

                    # Convert bbox points to Box
                    # bbox_points is a list of 4 corner points:
                    # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                    bbox_array = np.array(bbox_points)

                    # Find bounding rectangle
                    x_min = int(np.min(bbox_array[:, 0]))
                    y_min = int(np.min(bbox_array[:, 1]))
                    x_max = int(np.max(bbox_array[:, 0]))
                    y_max = int(np.max(bbox_array[:, 1]))

                    width = x_max - x_min
                    height = y_max - y_min

                    # Skip invalid boxes
                    if width <= 0 or height <= 0 or x_min < 0 or y_min < 0:
                        continue

                    box = Box(x=x_min, y=y_min, width=width, height=height)

                    result = OCRResult(text=text, confidence=float(confidence), box=box)
                    results.append(result)

                except (ValueError, IndexError, TypeError):
                    # Skip malformed results
                    continue

            return results

        except Exception as e:
            raise RuntimeError(f"EasyOCR detection failed: {e}")

    def get_backend_info(self) -> dict[str, Any]:
        """Get information about the backend.

        Returns:
            dict: Backend information
        """
        return {
            "name": "EasyOCR",
            "version": (
                easyocr.__version__ if hasattr(easyocr, "__version__") else "Unknown"
            ),
            "languages": self.languages,
            "gpu_enabled": self.gpu,
            "supported_languages": self.get_supported_languages(),
        }

    def get_supported_languages(self) -> list[str]:
        """Get list of supported languages.

        Returns:
            list[str]: List of supported language codes
        """
        try:
            # EasyOCR supported languages
            supported = [
                "en",
                "ch_sim",
                "ch_tra",
                "ja",
                "ko",
                "th",
                "vi",
                "ar",
                "hi",
                "bn",
                "ta",
                "te",
                "kn",
                "ml",
                "ne",
                "si",
                "my",
                "lo",
                "km",
                "ru",
                "bg",
                "uk",
                "be",
                "mk",
                "rs",
                "mn",
                "cs",
                "sk",
                "hr",
                "sl",
                "hu",
                "ro",
                "sq",
                "lv",
                "lt",
                "et",
                "mt",
                "ga",
                "cy",
                "is",
                "fo",
                "ms",
                "tl",
                "id",
                "sw",
                "yo",
                "ig",
                "ha",
                "am",
                "ti",
                "om",
                "so",
                "zu",
                "af",
                "oc",
                "br",
                "ca",
                "co",
                "eu",
                "gl",
                "la",
                "mi",
                "mt",
                "cy",
                "ga",
                "gd",
                "kw",
                "mg",
                "no",
                "da",
                "sv",
                "fi",
                "et",
                "lv",
                "lt",
                "pl",
                "cs",
                "sk",
                "hu",
                "ro",
                "hr",
                "sr",
                "bs",
                "me",
                "mk",
                "bg",
                "sq",
                "el",
                "tr",
                "az",
                "kk",
                "ky",
                "uz",
                "tj",
                "mn",
                "ka",
                "hy",
                "he",
                "ur",
                "fa",
                "ps",
                "sd",
                "ug",
                "bo",
                "dz",
                "km",
                "lo",
                "my",
                "si",
                "ta",
                "te",
                "kn",
                "ml",
                "or",
                "pa",
                "gu",
                "bn",
                "as",
                "mni",
                "hi",
                "mr",
                "ne",
                "bh",
                "mai",
                "ang",
                "bho",
                "mni",
                "sa",
            ]
            return supported
        except Exception:
            return ["en"]  # Default fallback

    def set_languages(self, languages: list[str]) -> None:
        """Change the languages for OCR recognition.

        Args:
            languages: List of language codes
        """
        if languages != self.languages:
            self.languages = languages
            # Reinitialize reader with new languages
            try:
                self.reader = easyocr.Reader(languages, gpu=self.gpu)
            except Exception as e:
                # Fallback to CPU if GPU fails
                if self.gpu:
                    try:
                        self.reader = easyocr.Reader(languages, gpu=False)
                        self.gpu = False
                    except Exception as e2:
                        raise RuntimeError(f"Failed to reinitialize EasyOCR: {e2}")
                else:
                    raise RuntimeError(f"Failed to reinitialize EasyOCR: {e}")

    def detect_and_recognize(
        self, image: np.ndarray, **kwargs
    ) -> tuple[list[OCRResult], str]:
        """Detect text with boxes and also return full text.

        Args:
            image: Input image as numpy array
            **kwargs: Additional arguments

        Returns:
            tuple: (list of OCRResult objects, combined text string)
        """
        ocr_results = self.detect_text_with_boxes(image, **kwargs)
        combined_text = " ".join(result.text for result in ocr_results)
        return ocr_results, combined_text
