"""Template Match Result class."""

from dataclasses import dataclass

from ..geometry import Box, Point


@dataclass(frozen=True)
class TemplateMatchResult:
    """Container for Template Match detection results."""

    template: str
    confidence: float
    box: Box

    def __str__(self) -> str:
        """Return a string representation of the Template Match result."""
        return (
            f"Template MatchResult(template='{self.template}', "
            f"confidence={self.confidence:.2f}, box={self.box})"
        )

    def with_offset(self, offset: Point) -> "TemplateMatchResult":
        """Return a new TemplateMatchResult with box coordinates offset.

        This is useful when TemplateMatch was performed on a cropped image, and you need
        to translate the coordinates back to the original image space.

        Args:
            offset: Point representing the offset to add to the box coordinates

        Returns:
            TemplateMatchResult: New Template MatchResult with adjusted box coordinates
        """
        new_top_left = Point(
            self.box.top_left.x + offset.x, self.box.top_left.y + offset.y
        )
        new_box = Box(new_top_left, self.box.width, self.box.height)
        return TemplateMatchResult(self.template, self.confidence, new_box)
