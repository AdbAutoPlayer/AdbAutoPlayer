"""Coordinates interface."""

from typing import Protocol


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
