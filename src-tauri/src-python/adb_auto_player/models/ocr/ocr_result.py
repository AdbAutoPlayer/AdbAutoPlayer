"""OCR Result class."""

from dataclasses import dataclass

from .. import ConfidenceValue
from ..geometry import Box, Coordinates, Point


@dataclass(frozen=True)
class OCRResult(Coordinates):
    """Container for OCR detection results."""

    text: str
    confidence: ConfidenceValue
    box: Box

    def __str__(self) -> str:
        """Return a string representation of the OCR result."""
        return (
            f"OCRResult(text='{self.text}', confidence={self.confidence}, "
            f"box={self.box})"
        )

    def with_offset(self, offset: Point) -> "OCRResult":
        """Return a new OCRResult with box coordinates offset by the given point.

        This is useful when OCR was performed on a cropped image, and you need
        to translate the coordinates back to the original image space.

        Args:
            offset: Point representing the offset to add to the box coordinates

        Returns:
            OCRResult: New OCRResult with adjusted box coordinates
        """
        new_top_left = Point(
            self.box.top_left.x + offset.x, self.box.top_left.y + offset.y
        )
        new_box = Box(new_top_left, self.box.width, self.box.height)
        return OCRResult(self.text, self.confidence, new_box)

    @property
    def x(self) -> int:
        """Center x-coordinate."""
        return self.box.x

    @property
    def y(self) -> int:
        """Center y-coordinate."""
        return self.box.y
