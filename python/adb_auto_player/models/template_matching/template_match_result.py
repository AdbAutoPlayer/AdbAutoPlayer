"""Template Match Result class."""

from dataclasses import dataclass

from ..geometry import Box, Coordinates, Point


@dataclass(frozen=True)
class TemplateMatchResult(Coordinates):
    """Container for Template Match detection results."""

    template: str
    confidence: float
    box: Box

    def __str__(self) -> str:
        """Return a string representation of the Template Match result."""
        return (
            f"TemplateMatchResult(template='{self.template}', "
            f"confidence={self.confidence:.2f}, box={self.box})"
        )

    def with_offset(self, offset: Point) -> "TemplateMatchResult":
        """Return a new TemplateMatchResult with box coordinates offset.

        Args:
            offset: Point representing the offset to add to the box coordinates

        Returns:
            TemplateMatchResult: New Template MatchResult with adjusted box coordinates
        """
        return TemplateMatchResult(
            template=self.template,
            confidence=self.confidence,
            box=self.box.with_offset(offset),
        )

    @property
    def x(self) -> int:
        """Center x-coordinate."""
        return self.box.x

    @property
    def y(self) -> int:
        """Center y-coordinate."""
        return self.box.y
