from dataclasses import dataclass
from enum import StrEnum


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

    width: int
    height: int
    orientation: Orientation

    @property
    def resolution(self) -> str:
        """Return device resolution."""
        return str(self.width) + "x" + str(self.height)

    @property
    def dimensions(self) -> tuple[int, int]:
        """Return device resolution tuple."""
        return self.width, self.height

    def __str__(self) -> str:
        """Return a string representation of the display info."""
        return (
            f"DisplayInfo(width={self.width}, height={self.height}, "
            f"orientation={self.orientation})"
        )
