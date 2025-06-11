"""Box class for geometric operations."""

import random
from dataclasses import dataclass

from .point import Point

# Constants
MAX_MARGIN_RATIO = 0.5


@dataclass(frozen=True)
class Box:
    """Box with top-left corner and dimensions."""

    x: int
    y: int
    width: int
    height: int

    def __post_init__(self):
        """Validate box coordinates and dimensions."""
        if self.x < 0 or self.y < 0:
            if self.x < 0 or self.y < 0:
                raise ValueError(
                    f"Invalid Box coordinates: x={self.x}, y={self.y}. "
                    "Both must be non-negative."
                )
        if self.width <= 0:
            raise ValueError(f"Box width must be positive, got: {self.width}")
        if self.height <= 0:
            raise ValueError(f"Box height must be positive, got: {self.height}")

    @property
    def left(self) -> int:
        """Get the left edge x-coordinate of the box."""
        return self.x

    @property
    def top(self) -> int:
        """Get the top edge y-coordinate of the box."""
        return self.y

    @property
    def right(self) -> int:
        """Get the right edge x-coordinate of the box."""
        return self.left + self.width

    @property
    def bottom(self) -> int:
        """Get the bottom edge y-coordinate of the box."""
        return self.top + self.height

    @property
    def top_left(self) -> Point:
        """Get the top-left corner point of the box."""
        return Point(self.left, self.top)

    @property
    def top_right(self) -> Point:
        """Get the top-right corner point of the box."""
        return Point(self.right, self.top)

    @property
    def bottom_left(self) -> Point:
        """Get the bottom-left corner point of the box."""
        return Point(self.left, self.bottom)

    @property
    def bottom_right(self) -> Point:
        """Get the bottom-right corner point of the box."""
        return Point(self.right, self.bottom)

    @property
    def center(self) -> Point:
        """Get the center point of the box."""
        return Point(self.x + self.width // 2, self.y + self.height // 2)

    @property
    def area(self) -> int:
        """Get the area of the box."""
        return self.width * self.height

    def random_point(self, margin: float | str = 0.0) -> Point:
        """Generate a random point inside the box, avoiding a margin near the edges.

        If there isn't enough room on one axis, returns center coordinate on that axis.

        Args:
            margin: Float between 0.0 and <0.5, or string like "10%"

        Returns:
            Point: Random point inside the safe area
        """
        if isinstance(margin, str):
            if not margin.endswith("%"):
                raise ValueError(f"Margin string must end with '%', got: '{margin}'")
            try:
                margin = float(margin.strip("%")) / 100.0
            except ValueError:
                raise ValueError(f"Invalid percentage value in margin: '{margin}'")

        if not (0.0 <= margin < MAX_MARGIN_RATIO):
            raise ValueError(
                f"Margin must be between 0.0 and less than {MAX_MARGIN_RATIO}"
            )

        x_min = self.x + int(self.width * margin)
        x_max = self.right - int(self.width * margin)
        y_min = self.y + int(self.height * margin)
        y_max = self.bottom - int(self.height * margin)

        x = self.center.x
        y = self.center.y

        if x_max > x_min:
            x = random.randint(x_min, x_max - 1)
        if y_max > y_min:
            y = random.randint(y_min, y_max - 1)

        return Point(x, y)

    def contains(self, point: Point) -> bool:
        """Check if a point is contained within the box.

        Args:
            point: The point to check

        Returns:
            bool: True if the point is inside the box, False otherwise
        """
        return self.left <= point.x < self.right and self.top <= point.y < self.bottom

    def __str__(self):
        """Return a string representation of the box."""
        return f"Box(x={self.x}, y={self.y}, w={self.width}, h={self.height})"
