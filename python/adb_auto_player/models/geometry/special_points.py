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
