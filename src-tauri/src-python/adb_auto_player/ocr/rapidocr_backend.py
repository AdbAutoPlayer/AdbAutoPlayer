"""RapidOCR backend implementation."""

import logging
from typing import Any

import numpy as np
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.ocr import OCRResult
from rapidocr import RapidOCR

from ._backend import OCRBackend

logger = logging.getLogger(__name__)


class RapidOCRBackend(OCRBackend):
    """RapidOCR backend for text detection.

    Faster alternative to Tesseract, especially on machines with GPU support.
    Uses the same OCRResult interface for compatibility.
    """

    def __init__(self) -> None:
        """Initialize RapidOCR backend (lazy-loaded on first use)."""
        self._engine: Any | None = None

    def _get_engine(self) -> Any:
        """Lazy-initialize the RapidOCR engine."""
        if self._engine is None:
            self._engine = RapidOCR()
        return self._engine

    def close(self) -> None:
        """Clean up resources."""
        self._engine = None

    def extract_text(
        self,
        image: np.ndarray,
    ) -> str:
        """Extract all text from an image as a single string.

        Args:
            image: Input image as numpy array (BGR or grayscale)

        Returns:
            Extracted text
        """
        engine = self._get_engine()
        result = engine(image)

        if result:
            # RapidOCR v3.7+ format
            if hasattr(result, "txts") and result.txts:
                return " ".join(result.txts).strip()

            # Fallback for list/tuple format
            texts = []
            results_list = result if isinstance(result, list) else [result]
            for line in results_list:
                if isinstance(line, (list, tuple)) and len(line) > 1:
                    texts.append(str(line[1]))
                elif isinstance(line, str):
                    texts.append(line)
            return " ".join(texts).strip()
        return ""

    def detect_text_blocks(
        self,
        image: np.ndarray,
        min_confidence: ConfidenceValue = ConfidenceValue(0.0),
    ) -> list[OCRResult]:
        """Detect text blocks and return results with bounding boxes.

        Compatible with TesseractBackend.detect_text_blocks interface.

        Args:
            image: Input image as numpy array
            min_confidence: Minimum confidence threshold

        Returns:
            List of OCR results with bounding boxes
        """
        try:
            engine = self._get_engine()
            result = engine(image)
        except Exception as e:
            logger.error(f"RapidOCR detection failed: {e}")
            return []

        ocr_results: list[OCRResult] = []

        if not result:
            return ocr_results

        # Handle RapidOCR v3.7+ format with .boxes, .txts, .scores
        if hasattr(result, "txts") and result.txts:
            boxes = result.boxes if hasattr(result, "boxes") else []
            scores = result.scores if hasattr(result, "scores") else []

            for i, text in enumerate(result.txts):
                stripped_text = text.strip()
                if not stripped_text:
                    continue

                confidence = scores[i] if i < len(scores) else 1.0
                if confidence < min_confidence.value:
                    continue

                # RapidOCR boxes are 4 corner points [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                if i < len(boxes) and boxes[i] is not None:
                    box_points = boxes[i]
                    x_coords = [p[0] for p in box_points]
                    y_coords = [p[1] for p in box_points]
                    min_x = int(min(x_coords))
                    min_y = int(min(y_coords))
                    max_x = int(max(x_coords))
                    max_y = int(max(y_coords))
                    width = max_x - min_x
                    height = max_y - min_y
                else:
                    # Fallback: use image dimensions
                    min_x, min_y = 0, 0
                    height, width = image.shape[:2]

                try:
                    box = Box(Point(x=min_x, y=min_y), width=width, height=height)
                    ocr_result = OCRResult(
                        text=stripped_text,
                        confidence=ConfidenceValue(confidence),
                        box=box,
                    )
                    ocr_results.append(ocr_result)
                except ValueError:
                    continue

        return ocr_results
