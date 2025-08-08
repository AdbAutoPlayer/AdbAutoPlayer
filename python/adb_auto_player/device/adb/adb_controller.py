import logging
from functools import lru_cache
from time import sleep

from adb_auto_player.decorators import register_cache
from adb_auto_player.exceptions import GameStartError, GenericAdbUnrecoverableError
from adb_auto_player.models.decorators import CacheGroup
from adb_auto_player.models.device import DisplayInfo, Orientation
from adb_auto_player.models.geometry import Coordinates

from .adb_device import AdbDeviceWrapper


class AdbController:
    """Functions to control an ADB device."""

    d: AdbDeviceWrapper

    def __init__(self):
        """Init."""
        self.d = AdbDeviceWrapper.create_from_settings()

    def set_display_size(self, display_size: str) -> None:
        """Set display size.

        Args:
            display_size: format width x height e.g. 1080x1920
        """
        _ = self.d.shell(f"wm size {display_size}")
        logging.info(f"Set Display Size to {display_size} for Device: {self.d.serial}")

    @register_cache(CacheGroup.ADB)
    @lru_cache(maxsize=1)
    def get_display_info(self) -> DisplayInfo:
        """Get display resolution and orientation.

        Raises:
            GenericAdbUnrecoverableError: Unable to determine screen resolution or
                orientation.

        Returns:
            DisplayInfo: Resolution and orientation.
        """
        result = self.d.shell("wm size")
        if not result:
            raise GenericAdbUnrecoverableError("Unable to determine screen resolution")

        # Parse resolution from wm size output
        lines: list[str] = result.splitlines()
        override_size = None
        physical_size = None

        for line in lines:
            if "Override size:" in line:
                override_size = line.split("Override size:")[-1].strip()
                logging.debug(f"Override size: {override_size}")
            elif "Physical size:" in line:
                physical_size = line.split("Physical size:")[-1].strip()
                logging.debug(f"Physical size: {physical_size}")

        resolution_str: str | None = override_size if override_size else physical_size

        if not resolution_str:
            raise GenericAdbUnrecoverableError(
                f"Unable to determine screen resolution: {result}"
            )

        try:
            width_str, height_str = resolution_str.split("x")
            width, height = int(width_str), int(height_str)
        except (ValueError, AttributeError):
            raise GenericAdbUnrecoverableError(
                f"Invalid resolution format: {resolution_str}"
            )

        device_orientation = _check_orientation(self.d)

        return DisplayInfo(
            width=width if Orientation.PORTRAIT == device_orientation else height,
            height=height if Orientation.PORTRAIT == device_orientation else width,
            orientation=device_orientation,
        )

    def get_running_app(self) -> str | None:
        """Get the currently running app.

        Returns:
            str | None: Currently running app name, or None if unable to determine.
        """
        app = str(
            self.d.shell(
                "dumpsys activity activities | grep ResumedActivity | "
                'cut -d "{" -f2 | cut -d \' \' -f3 | cut -d "/" -f1',
            )
        ).strip()
        if "\n" in app:
            app = app.split("\n")[0].strip()
        if app:
            return app
        return None

    def reset_display_size(self) -> None:
        """Resets the display size of the device to its original size."""
        self.d.shell("wm size reset")
        logging.info(f"Reset Display Size for Device: {self.d.serial}")

    def screenshot(self) -> str | bytes:
        """Take screenshot."""
        with self.d.shell("screencap -p", stream=True) as c:
            return c.read_until_close(encoding=None)

    def stop_game(self, package_name: str) -> None:
        """Stop game."""
        self.d.shell(["am", "force-stop", package_name])
        sleep(5)

    def start_game(self, package_name: str) -> None:
        """Start game."""
        output = self.d.shell(
            [
                "monkey",
                "-p",
                package_name,
                "-c",
                "android.intent.category.LAUNCHER",
                "1",
            ]
        )
        if "No activities found to run" in output:
            logging.debug(f"start_game: {output}")
            raise GameStartError("Game cannot be started")
        sleep(15)

    @property
    def identifier(self) -> str:
        """Device identifier."""
        return (
            self.d.serial if self.d.serial else self.d.info.get("serialno", "unknown")
        )

    def tap(
        self,
        coordinates: Coordinates,
    ) -> None:
        """Tap the screen on the given coordinates.

        Args:
            coordinates (Coordinates): Point to click on.
        """
        with self.d.shell(
            f"input tap {coordinates.x} {coordinates.y}",
            timeout=3,  # if the click didn't happen in 3 seconds it's never happening
            stream=True,
        ) as connection:
            connection.read_until_close()

    def click(
        self,
        coordinates: Coordinates,
    ) -> None:
        """Alias for tap."""
        self.tap(coordinates)

    def press_back_button(self) -> None:
        """Presses the back button."""
        with self.d.shell("input keyevent 4", stream=True) as connection:
            connection.read_until_close()

    def press_enter(self) -> None:
        """Press enter button."""
        with self.d.shell("input keyevent 66", stream=True) as connection:
            connection.read_until_close()

    def swipe(
        self,
        start_point: Coordinates,
        end_point: Coordinates,
        duration: float = 1.0,
        sleep_duration: float | None = 2.0,
    ) -> None:
        """Swipes the screen.

        Args:
            start_point: Start Point on the screen.
            end_point: End Point on the screen.
            duration: Swipe duration. Defaults to 1.0.
            sleep_duration: Sleep duration. Defaults to 2.0. No sleep if None
        """
        with self.d.shell(
            [
                "input",
                "swipe",
                str(start_point.x),
                str(start_point.y),
                str(end_point.x),
                str(end_point.y),
                str(int(duration * 1000)),
            ],
            stream=True,
        ) as connection:
            connection.read_until_close()
        if sleep_duration is None:
            sleep_duration = 1 / 30
        sleep(sleep_duration)

    def hold(
        self,
        coordinates: Coordinates,
        duration: float = 1.0,
        sleep_duration: float | None = 1 / 30,
    ) -> None:
        """Hold the screen on the given coordinates."""
        self.swipe(
            start_point=coordinates,
            end_point=coordinates,
            duration=duration,
            sleep_duration=sleep_duration,
        )

    @property
    @register_cache(CacheGroup.ADB)
    @lru_cache(maxsize=1)
    def is_controlling_emulator(self):
        """Whether the controlled device is an emulator or not."""
        result = str(self.d.shell('getprop | grep "Build"'))
        if "Build" in result:
            return True
        logging.debug('getprop does not contain "Build" assuming Phone')
        return False


def _check_orientation(d: AdbDeviceWrapper) -> Orientation:
    """Check device orientation using multiple fallback methods.

    Tries different orientation detection methods in order of reliability,
    returning as soon as a definitive result is found. Portrait orientation
    corresponds to rotation 0, while landscape corresponds to rotations 1 and 3.

    Args:
        d (AdbDevice): ADB device.

    Returns:
        Orientation: Device orientation (PORTRAIT or LANDSCAPE).

    Raises:
        GenericAdbUnrecoverableError: If unable to perform any orientation checks.
    """
    # Check 1: SurfaceOrientation (most reliable)
    try:
        orientation_check = str(
            d.shell("dumpsys input | grep 'SurfaceOrientation'")
        ).strip()
        if orientation_check:
            if "Orientation: 0" in orientation_check:
                return Orientation.PORTRAIT
            elif any(
                x in orientation_check for x in ["Orientation: 1", "Orientation: 3"]
            ):
                return Orientation.LANDSCAPE
        logging.debug(f"orientation_check: {orientation_check}")
    except Exception as e:
        logging.debug(f"SurfaceOrientation check failed: {e}")

    # Check 2: Current rotation (fallback)
    try:
        rotation_check = str(
            d.shell_unsafe("dumpsys window | grep mCurrentRotation")
        ).strip()
        if rotation_check:
            if "ROTATION_0" in rotation_check:
                return Orientation.PORTRAIT
            elif any(x in rotation_check for x in ["ROTATION_90", "ROTATION_270"]):
                return Orientation.LANDSCAPE
        logging.debug(f"rotation_check: {rotation_check}")
    except Exception as e:
        logging.debug(f"Rotation check failed: {e}")

    # Check 3: Display orientation (last resort)
    try:
        display_check = str(
            d.shell_unsafe("dumpsys display | grep -E 'orientation'")
        ).strip()
        if display_check:
            if "orientation=0" in display_check:
                return Orientation.PORTRAIT
            elif any(x in display_check for x in ["orientation=1", "orientation=3"]):
                return Orientation.LANDSCAPE
        logging.debug(f"display_check: {display_check}")
    except Exception as e:
        logging.debug(f"Display orientation check failed: {e}")

    raise GenericAdbUnrecoverableError("Unable to determine device orientation")
