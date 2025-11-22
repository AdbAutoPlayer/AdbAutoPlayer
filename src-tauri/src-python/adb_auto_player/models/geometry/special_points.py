from .coordinates import Coordinates


class PointOutsideDisplay(Coordinates):
    """Special Point that is outside display bounds.

    Mainly used to test click delay on Adb.
    """

    @property
    def x(self) -> int:
        """X-coordinate."""
        return -1

    @property
    def y(self) -> int:
        """Y-coordinate."""
        return -1


class Offset(Coordinates):
    """A 2D coordinate for calculations, allowing negative integers."""

    def __init__(self, x: int, y: int):
        self._x = x
        self._y = y

    @property
    def x(self) -> int:
        """X-coordinate."""
        return self._x

    @property
    def y(self) -> int:
        """Y-coordinate."""
        return self._y
