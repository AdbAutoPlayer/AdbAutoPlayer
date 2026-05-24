"""Abstract base class for OCR backends."""

from abc import ABC, abstractmethod

import numpy as np
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.ocr import OCRResult


class OCRBackend(ABC):
    """Common interface for OCR backend implementations.

    Both :class:`RapidOCRBackend` and :class:`TesseractBackend` implement this
    interface so callers can swap backends without changing call sites.
    """

    @abstractmethod
    def extract_text(self, image: np.ndarray) -> str:
        """Extract all text from an image as a single string.

        Args:
            image: Input image as numpy array (BGR or grayscale).

        Returns:
            Extracted text, stripped of leading/trailing whitespace.
        """
        ...

    @abstractmethod
    def detect_text_blocks(
        self,
        image: np.ndarray,
        min_confidence: ConfidenceValue = ConfidenceValue(0.0),
    ) -> list[OCRResult]:
        """Detect text blocks and return results with bounding boxes.

        Args:
            image: Input image as numpy array.
            min_confidence: Minimum confidence threshold for results.

        Returns:
            List of OCRResult objects, each with text, confidence and bounding box.
        """
        ...
