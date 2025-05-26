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


class AutoPlayerPanicError(AutoPlayerError):
    """Base class for critical errors that should halt the program."""

    pass


class GenericAdbError(AutoPlayerPanicError):
    """Raised for any Adb related issues."""

    pass


class NotInitializedError(AutoPlayerPanicError):
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


class GameStartError(AutoPlayerPanicError):
    """Raised when the Game cannot be started."""

    pass


class UnsupportedResolutionError(AutoPlayerPanicError):
    """Raised when the resolution is not supported."""

    pass
