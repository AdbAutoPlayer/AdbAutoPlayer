"""ADB errors."""

from .base import AutoPlayerError, AutoPlayerUnrecoverableError


class GenericAdbError(AutoPlayerError):
    """Raised for any ADB-related issues."""

    pass


class GenericAdbUnrecoverableError(AutoPlayerUnrecoverableError):
    """Raised for non-recoverable ADB-related errors."""

    pass
