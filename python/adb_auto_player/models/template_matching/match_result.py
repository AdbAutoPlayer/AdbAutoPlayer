"""match_result module."""

from dataclasses import dataclass

from .. import ConfidenceValue
from ..geometry import Box, Coordinates, Point
from .template_match_result import TemplateMatchResult


@dataclass(frozen=True)
class MatchResult(Coordinates):
    """Represents the result of a matching operation."""

    box: Box
    confidence: ConfidenceValue

    def with_offset(self, offset: Point) -> "MatchResult":
        """Return a new MatchResult with box coordinates offset.

        Args:
            offset: Point representing the offset to add to the box coordinates

        Returns:
            MatchResult: New Template MatchResult with adjusted box coordinates
        """
        return MatchResult(
            box=self.box.with_offset(offset),
            confidence=self.confidence,
        )

    def to_template_match_result(self, template: str) -> TemplateMatchResult:
        """Generate a TemplateMatchResult."""
        return TemplateMatchResult(
            box=self.box,
            confidence=self.confidence,
            template=template,
        )

    def __str__(self) -> str:
        """Return a string representation of the MatchResult."""
        return f"MatchResult(confidence={self.confidence}, box={self.box})"

    @property
    def x(self) -> int:
        """Center x-coordinate."""
        return self.box.x

    @property
    def y(self) -> int:
        """Center y-coordinate."""
        return self.box.y
