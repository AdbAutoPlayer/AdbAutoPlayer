"""ADB Auto Player Custom Exceptions Module."""


class BaseAutoPlayerError(Exception):
    """Base exception for all custom ADB Auto Player exceptions."""

    pass


class AutoPlayerWarningError(BaseAutoPlayerError):
    """Base class for non-critical warnings."""

    pass


class AutoPlayerError(BaseAutoPlayerError):
    """Base class for recoverable errors."""

    pass


class AutoPlayerUnrecoverableError(BaseAutoPlayerError):
    """Base class for critical errors that should halt the program."""

    pass


class GenericAdbUnrecoverableError(AutoPlayerUnrecoverableError):
    """Raised for non-recoverable ADB related errors."""

    pass


class GenericAdbError(AutoPlayerError):
    """Raised for any Adb related issues."""

    pass


class NotInitializedError(AutoPlayerUnrecoverableError):
    """Required variable not initialized."""

    pass


class GameTimeoutError(AutoPlayerError):
    """Raised when an operation exceeds the given timeout."""

    pass


class GameActionFailedError(AutoPlayerError):
    """Generic Exception that can be used when any action fails."""

    pass


class GameNotRunningOrFrozenError(AutoPlayerError):
    """Raised when the Game is not running."""

    pass


class GameStartError(AutoPlayerUnrecoverableError):
    """Raised when the Game cannot be started."""

    pass


class UnsupportedResolutionError(AutoPlayerUnrecoverableError):
    """Raised when the resolution is not supported."""

    pass
