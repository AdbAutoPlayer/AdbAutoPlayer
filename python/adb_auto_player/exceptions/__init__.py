"""Exceptions package.

Exceptions should not have dependencies on other internal packages.
"""

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
from .pydantic import (
    InvalidBoundaryError,
    InvalidDefaultValueError,
    MissingBoundaryValueError,
    MissingDefaultValueError,
    RegexMissingTitleError,
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
    "InvalidBoundaryError",
    "InvalidDefaultValueError",
    "MissingBoundaryValueError",
    "MissingDefaultValueError",
    "NotInitializedError",
    "RegexMissingTitleError",
    "UnsupportedResolutionError",
]
