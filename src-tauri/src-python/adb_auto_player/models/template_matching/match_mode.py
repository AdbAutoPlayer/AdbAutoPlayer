"""Template Matching match modes."""

from enum import StrEnum, auto


class MatchMode(StrEnum):
    """Match mode as a sting-based enum."""

    BEST = auto()
    TOP_LEFT = auto()
    TOP_RIGHT = auto()
    BOTTOM_LEFT = auto()
    BOTTOM_RIGHT = auto()
    LEFT_TOP = auto()
    LEFT_BOTTOM = auto()
    RIGHT_TOP = auto()
    RIGHT_BOTTOM = auto()
