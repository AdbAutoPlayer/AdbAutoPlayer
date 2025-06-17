"""OCR engines with pluggable backends for text detection and extraction."""

from abc import ABC, abstractmethod
from typing import Any

import numpy as np
from adb_auto_player.models.ocr.ocr_result import OCRResult


class OCRBackend(ABC):
    """Abstract base class for OCR backends."""

    @abstractmethod
    def extract_text(self, image: np.ndarray, **kwargs) -> str:
        """Extract all text from an image as a single string."""
        pass

    @abstractmethod
    def detect_text_with_boxes(self, image: np.ndarray, **kwargs) -> list[OCRResult]:
        """Detect text and return results with bounding boxes."""
        pass

    @abstractmethod
    def get_backend_info(self) -> dict[str, Any]:
        """Get information about the backend."""
        pass
