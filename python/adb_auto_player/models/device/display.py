from dataclasses import dataclass
from enum import StrEnum

from ..geometry import Point


class Orientation(StrEnum):
    """Device orientation enum."""

    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


@dataclass(frozen=True)
class Resolution:
    """Display Resolution dataclass."""

    width: int
    height: int

    @classmethod
    def from_string(cls, res: str) -> "Resolution":
        """Create a Resolution from a width x height string."""
        try:
            width, height = map(int, res.lower().replace(" ", "").split("x"))

            if width <= 0 or height <= 0:
                raise ValueError("Dimensions must be positive")
            return cls(width, height)
        except (ValueError, AttributeError) as e:
            raise ValueError(
                f"Invalid resolution format: '{res}' (expected 'WIDTHxHEIGHT')"
            ) from e

    def __str__(self) -> str:
        """String representation as width x height resolution."""
        return f"{self.width}x{self.height}"

    @property
    def is_landscape(self) -> bool:
        """Whether the resolution is landscape."""
        return self.width > self.height

    @property
    def is_portrait(self) -> bool:
        """Whether the resolution is portrait."""
        return self.height > self.width

    @property
    def dimensions(self) -> tuple[int, int]:
        """Return device resolution tuple."""
        return self.width, self.height

    @property
    def center(self) -> Point:
        """Return center Point of display."""
        return Point(self.width // 2, self.height // 2)

    @property
    def is_square(self) -> bool:
        """Whether the resolution is square."""
        return self.width == self.height

    @property
    def orientation(self) -> Orientation | None:
        """Return the resolution's orientation, or None if square."""
        if self.width > self.height:
            return Orientation.LANDSCAPE
        elif self.height > self.width:
            return Orientation.PORTRAIT
        return None


@dataclass(frozen=True)
class DisplayInfo:
    """Data class containing device display information.

    Orientation can change technically but if the user changes it while the bot is
    running then I'm not dealing with that so this is frozen.
    """

    resolution: Resolution
    orientation: Orientation | None

    @property
    def dimensions(self) -> tuple[int, int]:
        """Return device resolution tuple."""
        return self.normalized_resolution.dimensions

    @property
    def normalized_resolution(self) -> Resolution:
        """Return the resolution adjusted for the current orientation.

        Devices report the raw physical size even when the actual display is rotated.
        This normalizes width/height to match the current orientation.
        """
        res = self.resolution

        if self.orientation == Orientation.LANDSCAPE and res.height > res.width:
            return Resolution(width=res.height, height=res.width)

        if self.orientation == Orientation.PORTRAIT and res.width > res.height:
            return Resolution(width=res.height, height=res.width)

        return res

    def __str__(self) -> str:
        """Return a string representation of the display info."""
        return (
            f"DisplayInfo(resolution={self.resolution}, orientation={self.orientation})"
        )
