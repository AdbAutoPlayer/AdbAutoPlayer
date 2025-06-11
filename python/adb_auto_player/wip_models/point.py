"""Point class for geometric operations."""

import math
from dataclasses import dataclass

import numpy as np


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

    def is_close_to(self, other: "Point", threshold: int) -> bool:
        """Check if this point is within threshold distance of another point."""
        return self.distance_to(other) < threshold

    @classmethod
    def from_numpy(cls, array: np.ndarray) -> "Point":
        """Create Point from numpy array."""
        return cls(int(array[0]), int(array[1]))

    def to_numpy(self) -> np.ndarray:
        """Convert Point to numpy array."""
        return np.array([self.x, self.y])
