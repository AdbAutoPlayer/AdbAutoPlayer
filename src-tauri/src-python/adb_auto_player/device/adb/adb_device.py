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
        """Create a new AdbDeviceWrapper instance from ADB Settings."""
        return AdbDeviceWrapper(d=AdbClientHelper.resolve_adb_device())

    @adb_retry
    def shell(
        self,
        cmdargs: str | list | tuple,
        stream: bool = False,
        timeout: float | None = default_socket_timeout,
        encoding: str | None = "utf-8",
        rstrip: bool = True,
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
    def screenshot(self, display_id: str | None = None) -> str | bytes:
        """Screenshot.

        Args:
            display_id: Physical display id (as reported by
                `dumpsys SurfaceFlinger --display-id`) to capture from. Pass None to let
                adb pick its default display.

        Returns:
            str | bytes: Adb screencap response this can be a message too.
        """
        cmd = "screencap -p" if display_id is None else f"screencap -p -d {display_id}"
        with self.d.shell(cmd, stream=True) as c:
            return c.read_until_close(encoding=None)

    @staticmethod
    def _input_cmdargs(display_id: str | None, *args: str) -> list[str]:
        """Build an `input` shell command, optionally targeting a specific display.

        Args:
            display_id: WM logical display id (see `dumpsys window displays`), or None
                to let Android route the event to whichever display currently has
                input focus.
            *args: The `input` subcommand and its arguments, e.g. "tap", x, y.
        """
        cmdargs = ["input"]
        if display_id is not None:
            cmdargs.extend(["-d", display_id])
        cmdargs.extend(args)
        return cmdargs

    @adb_retry
    def tap(self, x: str, y: str, display_id: str | None = None) -> None:
        """Tap.

        Args:
            x: x coordinate
            y: y coordinate
            display_id: WM logical display id to target, or None for the default.
        """
        with self.d.shell(
            self._input_cmdargs(display_id, "tap", x, y),
            timeout=3,  # if the click didn't happen in 3 seconds it's never happening
            stream=True,
        ) as connection:
            connection.read_until_close()

    @adb_retry
    def keyevent(self, key: str, display_id: str | None = None) -> None:
        """Key event.

        Args:
            key: key code
            display_id: WM logical display id to target, or None for the default.
        """
        with self.d.shell(
            self._input_cmdargs(display_id, "keyevent", key), stream=True
        ) as connection:
            connection.read_until_close()

    @adb_retry
    def swipe(
        self,
        sx: str,
        sy: str,
        ex: str,
        ey: str,
        duration: str,
        *,
        display_id: str | None = None,
    ) -> None:
        """Swipe from sx, sy to ex, ey over duration ms.

        Args:
            sx: start X-coordinate.
            sy: start Y-coordinate.
            ex: end X-coordinate.
            ey: end Y-coordinate.
            duration: Swipe duration in milliseconds.
            display_id: WM logical display id to target, or None for the default.
        """
        with self.d.shell(
            self._input_cmdargs(display_id, "swipe", sx, sy, ex, ey, duration),
            stream=True,
        ) as connection:
            connection.read_until_close()

    def shell_unsafe(
        self,
        cmdargs: str | list | tuple,
        stream: bool = False,
        timeout: float | None = default_socket_timeout,
        encoding: str | None = "utf-8",
        rstrip: bool = True,
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
