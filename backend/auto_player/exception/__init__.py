"""Auto Player Exceptions Package."""

from .exceptions import (
    GameTimeoutError,
    GenericAdbError,
    NoPreviousScreenshotError,
    NotFoundError,
    NotInitializedError,
    UnsupportedResolutionError,
)

__all__: list[str] = [
    "GameTimeoutError",
    "GenericAdbError",
    "NoPreviousScreenshotError",
    "NotFoundError",
    "NotInitializedError",
    "UnsupportedResolutionError",
]
