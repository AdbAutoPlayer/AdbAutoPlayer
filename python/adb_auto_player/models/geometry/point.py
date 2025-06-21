"""Point class for geometric operations."""

import math
from dataclasses import dataclass

import numpy as np
from adb_auto_player.util.type_helpers import to_int_if_needed

from .coordinates import Coordinates


@dataclass
class Point(Coordinates):
    """A point in 2D space with non-negative integer coordinates."""

    def __init__(self, x: int, y: int):
        """Initialize point with x, y-coordinates."""
        if x < 0 or y < 0:
            raise ValueError(
                f"Invalid Point coordinates: x={x}, y={y}. Both must be non-negative."
            )
        self._x = x
        self._y = y

    def __post_init__(self):
        """Validate that coordinates are non-negative."""
        if self.x < 0 or self.y < 0:
            raise ValueError(
                f"Invalid Point coordinates: x={self.x}, y={self.y}. "
                "Both must be non-negative."
            )

    @property
    def x(self) -> int:
        """X-coordinate."""
        return self._x

    @property
    def y(self) -> int:
        """Y-coordinate."""
        return self._y

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

    def to_tuple(self) -> tuple[int, int]:
        """Convert to tuple (x,y) with dtype int."""
        return self.x, self.y

    def scale(self, scale_factor: float | None) -> "Point":
        """Return a new Point with coordinates scaled by the given scale factor.

        Raises:
            ValueError: If the scale factor is negative.
        """
        if scale_factor is None:
            return self

        if scale_factor < 0:
            raise ValueError(f"Scale factor must be non-negative, got {scale_factor}")

        if scale_factor == 1.0:
            return self  # no change needed

        new_x = max(0, round(self.x * scale_factor))
        new_y = max(0, round(self.y * scale_factor))

        return Point(new_x, new_y)

    def __str__(self):
        """Return a string representation of the point."""
        return f"Point(x={int(self.x)}, y={int(self.y)})"

    def __repr__(self):
        """Return a string representation of the point."""
        return f"Point(x={int(self.x)}, y={int(self.y)})"

    def __add__(self, other: "Point") -> "Point":
        """Creates a new Point with coordinates added to this point."""
        if not isinstance(other, Point):
            return NotImplemented
        new_x = self.x + other.x
        new_y = self.y + other.y
        return Point(new_x, new_y)
