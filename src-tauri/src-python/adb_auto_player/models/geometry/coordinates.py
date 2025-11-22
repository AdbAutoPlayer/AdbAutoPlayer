"""Coordinates interface."""

import math
from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class Coordinates(Protocol):
    """Protocol for objects with x, y-coordinates."""

    @property
    def x(self) -> int:
        """X-coordinate."""
        ...

    @property
    def y(self) -> int:
        """Y-coordinate."""
        ...

    def distance_to(self, other: "Coordinates") -> float:
        """Calculate Euclidean distance to another point."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def is_close_to(self, other: "Coordinates", threshold: float) -> bool:
        """Check if this point is within threshold distance of another point."""
        return self.distance_to(other) < threshold

    def as_adb_shell_str(self) -> str:
        """Return coordinates as a string formatted for adb shell commands."""
        return f"{self.x} {self.y}"

    def to_numpy(self) -> np.ndarray:
        """Convert Point to numpy array of shape (2,) with dtype int."""
        return np.array([self.x, self.y])

    def to_tuple(self) -> tuple[int, int]:
        """Convert to tuple (x,y) with dtype int."""
        return self.x, self.y
