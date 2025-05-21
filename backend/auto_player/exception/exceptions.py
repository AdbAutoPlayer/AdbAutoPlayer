"""Auto Player Custom Exceptions Module."""


class AutoPlayerError(Exception):
    """Base class for exceptions in this module."""

    pass


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


class GameTimeoutError(AutoPlayerError):
    """Exception raised when a game operation times out."""

    pass


class GameNotRunningError(Exception):
    """Raised when the Game is not running."""

    pass


class GameStartError(Exception):
    """Raised when the Game cannot be started."""

    pass


class UnsupportedResolutionError(Exception):
    """Raised when the resolution is not supported."""

    pass


class DeviceNotFoundError(AutoPlayerError):
    """Raised when a specified device cannot be found or connected to."""

    pass


class ConnectionError(AutoPlayerError):
    """Raised for errors that occur during a device connection (e.g., server issues)."""

    pass


class DeviceCommandError(AutoPlayerError):
    """Raised when a device command fails to execute or returns an error."""

    def __init__(self, command: str, message: str, stderr: str | None = None) -> None:
        super().__init__(f"Command '{command}' failed: {message}")
        self.command = command
        self.stderr = stderr

    pass
