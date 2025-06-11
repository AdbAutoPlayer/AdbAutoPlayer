"""Point class for geometric operations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    """A point in 2D space with non-negative integer coordinates."""

    x: int
    y: int

    def __post_init__(self):
        """Validate that coordinates are non-negative."""
        if self.x < 0 or self.y < 0:
            raise ValueError(
                f"Invalid Point coordinates: x={self.x}, y={self.y}. "
                "Both must be non-negative."
            )
