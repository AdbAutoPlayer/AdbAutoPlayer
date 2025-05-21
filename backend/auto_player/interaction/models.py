"""Models for interaction."""

from dataclasses import dataclass

@dataclass(frozen=True)
class Coordinates:
    """Represents a 2D coordinate.

    Attributes:
        x: The x-coordinate.
        y: The y-coordinate.
    """
    x: int
    y: int
