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

    def swipe(
        self, sx: int, sy: int, ex: int, ey: int, duration: float = 1.0
    ) -> AdbConnection | str | bytes:
        """Swipe with retry."""
        x1, y1, x2, y2 = map(str, [sx, sy, ex, ey])
        return self.shell(["input", "swipe", x1, y1, x2, y2, str(int(duration * 1000))])

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
