"""Exceptions module."""

from .adb import (
    GenericAdbError,
    GenericAdbUnrecoverableError,
)
from .base import (
    AutoPlayerError,
    AutoPlayerUnrecoverableError,
    AutoPlayerWarningError,
    BaseAutoPlayerError,
)
from .game import (
    GameActionFailedError,
    GameNotRunningOrFrozenError,
    GameStartError,
    GameTimeoutError,
    NotInitializedError,
    UnsupportedResolutionError,
)

__all__ = [
    "AutoPlayerError",
    "AutoPlayerUnrecoverableError",
    "AutoPlayerWarningError",
    "BaseAutoPlayerError",
    "GameActionFailedError",
    "GameNotRunningOrFrozenError",
    "GameStartError",
    "GameTimeoutError",
    "GenericAdbError",
    "GenericAdbUnrecoverableError",
    "NotInitializedError",
    "UnsupportedResolutionError",
]
