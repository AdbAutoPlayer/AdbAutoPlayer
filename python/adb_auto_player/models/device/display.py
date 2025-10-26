from dataclasses import dataclass
from enum import StrEnum

from ..geometry import Point


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
        return self.width >= self.height

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


class Orientation(StrEnum):
    """Device orientation enum."""

    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


@dataclass(frozen=True)
class DisplayInfo:
    """Data class containing device display information.

    Orientation can change technically but if the user changes it while the bot is
    running then I'm not dealing with that so this is frozen.
    """

    resolution: Resolution
    orientation: Orientation

    @property
    def dimensions(self) -> tuple[int, int]:
        """Return device resolution tuple."""
        return self.resolution.dimensions

    def __str__(self) -> str:
        """Return a string representation of the display info."""
        return (
            f"DisplayInfo(resolution={self.resolution}, orientation={self.orientation})"
        )
