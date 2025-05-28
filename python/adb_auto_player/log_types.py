"""Log Types for logging presets (color, ...)."""

from enum import Enum, auto


class LogType(Enum):
    """Enum representing different types of log events in the system."""

    DEFEAT = auto()
