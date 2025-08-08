from adb_auto_player.exceptions import GenericAdbUnrecoverableError
from adbutils import AdbConnection, AdbDevice

from .adb_client import AdbClientHelper
from .retry_decorator import adb_retry


def _check_output_for_error(output: AdbConnection | str | bytes):
    if not isinstance(output, str):
        return

    if "java.lang.SecurityException" in output:
        raise GenericAdbUnrecoverableError("java.lang.SecurityException")


class AdbDeviceWrapper:
    """Wrapper class for AdbDevice to add retry logic."""

    d: AdbDevice
    default_socket_timeout: float = 10.0

    def __init__(self, d: AdbDevice):
        """Init."""
        self.d = d

    @staticmethod
    def create_from_settings() -> "AdbDeviceWrapper":
        """Create a new AdbDeviceWrapper instance from General Settings."""
        return AdbDeviceWrapper(d=AdbClientHelper.resolve_adb_device())

    @adb_retry
    def shell(
        self,
        cmdargs: str | list | tuple,
        stream: bool = False,
        timeout: float | None = default_socket_timeout,
        encoding: str | None = "utf-8",
        rstrip=True,
    ) -> AdbConnection | str | bytes:
        """Shell with retry."""
        output = self.d.shell(
            cmdargs=cmdargs,
            stream=stream,
            timeout=timeout,
            encoding=encoding,
            rstrip=rstrip,
        )

        _check_output_for_error(output)
        return output

    @adb_retry
    def screenshot(self) -> str | bytes:
        """Screenshot.

        Returns:
            str | bytes: Adb screencap response this can be a message too.
        """
        with self.d.shell("screencap -p", stream=True) as c:
            return c.read_until_close(encoding=None)

    @adb_retry
    def tap(self, x: str, y: str) -> None:
        """Tap.

        Args:
            x: x coordinate
            y: y coordinate
        """
        with self.d.shell(
            [
                "input",
                "tap",
                x,
                y,
            ],
            timeout=3,  # if the click didn't happen in 3 seconds it's never happening
            stream=True,
        ) as connection:
            connection.read_until_close()

    @adb_retry
    def keyevent(self, key: str) -> None:
        """Key event.

        Args:
            key: key code
        """
        with self.d.shell(["input", "keyevent", key], stream=True) as connection:
            connection.read_until_close()

    @adb_retry
    def swipe(self, sx: str, sy: str, ex: str, ey: str, duration: str) -> None:
        """Swipe from sx, sy to ex, ey over duration ms.

        Args:
            sx: start X-coordinate.
            sy: start Y-coordinate.
            ex: end X-coordinate.
            ey: end Y-coordinate.
            duration: Swipe duration in milliseconds.
        """
        with self.d.shell(
            [
                "input",
                "swipe",
                sx,
                sy,
                ex,
                ey,
                duration,
            ],
            stream=True,
        ) as connection:
            connection.read_until_close()

    def shell_unsafe(
        self,
        cmdargs: str | list | tuple,
        stream: bool = False,
        timeout: float | None = default_socket_timeout,
        encoding: str | None = "utf-8",
        rstrip=True,
    ) -> AdbConnection | str | bytes:
        """Shell without retry.

        Should not be used really unless you have a good reason.
        """
        output = self.d.shell(
            cmdargs=cmdargs,
            stream=stream,
            timeout=timeout,
            encoding=encoding,
            rstrip=rstrip,
        )

        return output

    @property
    def serial(self) -> str | None:
        """Device serial."""
        return self.d.serial

    @property
    def info(self) -> dict:
        """Serialno (real serial number), devpath, state."""
        return self.d.info
