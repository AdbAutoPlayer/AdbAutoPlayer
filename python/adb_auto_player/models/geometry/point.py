"""Point class for geometric operations."""

import math
from dataclasses import dataclass

import numpy as np
from adb_auto_player.util.type_helpers import to_int_if_needed


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

    def distance_to(self, other: "Point") -> float:
        """Calculate Euclidean distance to another point."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def is_close_to(self, other: "Point", threshold: float) -> bool:
        """Check if this point is within threshold distance of another point."""
        return self.distance_to(other) < threshold

    @classmethod
    def from_numpy(cls, array: np.ndarray) -> "Point":
        """Create Point from numpy array."""
        assert array.shape == (2,), "Input array must be 1-dimensional with 2 elements"

        x = to_int_if_needed(array[0])
        y = to_int_if_needed(array[1])
        return cls(x, y)

    def to_numpy(self) -> np.ndarray:
        """Convert Point to numpy array of shape (2,) with dtype int."""
        return np.array([self.x, self.y])

    def __str__(self):
        """Return a string representation of the point."""
        return f"Point(x={int(self.x)}, y={int(self.y)})"
