"""Errors that will be thrown in games but are not specific to 1 game."""

from .base import AutoPlayerError, AutoPlayerUnrecoverableError


class GameTimeoutError(AutoPlayerError):
    """Raised when an operation exceeds the given timeout."""

    pass


class GameActionFailedError(AutoPlayerError):
    """Generic Exception that can be used when any action fails."""

    pass


class GameNotRunningOrFrozenError(AutoPlayerError):
    """Raised when the game is not running or has frozen."""

    pass


class GameStartError(AutoPlayerUnrecoverableError):
    """Raised when the game cannot be started."""

    pass


class UnsupportedResolutionError(AutoPlayerUnrecoverableError):
    """Raised when the resolution is not supported."""

    pass


class NotInitializedError(AutoPlayerUnrecoverableError):
    """Required variable not initialized."""

    pass
