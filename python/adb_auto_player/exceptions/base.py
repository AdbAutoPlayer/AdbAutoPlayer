"""Base error classes other errors should implement these."""


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
