"""OCR Result class."""

from dataclasses import dataclass

from ..geometry.box import Box


@dataclass(frozen=True)
class OCRResult:
    """Container for OCR detection results."""

    text: str
    confidence: float
    box: Box

    def __str__(self) -> str:
        """Return a string representation of the OCR result."""
        return (
            f"OCRResult(text='{self.text}', confidence={self.confidence:.2f}, "
            f"box={self.box})"
        )
