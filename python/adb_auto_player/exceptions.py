"""ADB Auto Player Custom Exceptions Module."""


class GenericAdbError(Exception):
    """Raised for any Adb related issues."""

    pass


class NotFoundError(Exception):
    """Image not found."""

    pass


class NoPreviousScreenshotError(Exception):
    """Previous Screenshot required but does not exist."""

    pass


class NotInitializedError(Exception):
    """Required variable not initialized."""

    pass


class GameTimeoutError(Exception):
    """Raised when an operation exceeds the given timeout."""

    pass


class GameActionFailedError(Exception):
    """Generic Exception that can be used when any action fails."""

    pass


class GameAdvisoryWarningError(Exception):
    """Raised when an expected but non-critical condition occurs."""

    pass


class GameNotRunningOrFrozenError(Exception):
    """Raised when the Game is not running."""

    pass


class GameStartError(Exception):
    """Raised when the Game cannot be started."""

    pass


class UnsupportedResolutionError(Exception):
    """Raised when the resolution is not supported."""

    pass
