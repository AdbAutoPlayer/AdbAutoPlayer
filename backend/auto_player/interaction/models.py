"""Models for interaction."""

from dataclasses import dataclass
from typing import NamedTuple


@dataclass(frozen=True)
class Coordinates:
    """Represents a 2D coordinate.

    Attributes:
        x: The x-coordinate.
        y: The y-coordinate.
    """

    x: int
    y: int


class InteractionWait(NamedTuple):
    """Defines optional wait times before, during, and after an interaction.

    Attributes:
        before: Wait time in milliseconds before the interaction starts.
        during: Wait time in milliseconds during the interaction (e.g., hold time).
        after: Wait time in milliseconds after the interaction completes.
    """

    before: int = 0
    during: int = 0
    after: int = 0


@dataclass(frozen=True)
class KeyEvent:
    """Represents a key event.

    Attributes:
        identifier: A string (e.g., "ENTER", "KEYCODE_HOME") or an integer code
                    representing the key.
    """

    identifier: str | int
