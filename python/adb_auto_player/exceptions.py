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


class TimeoutError(Exception):
    """Raised when an operation exceeds the given timeout."""

    pass


class UnsupportedResolutionError(Exception):
    """Raised when the resolution is not supported."""

    pass
