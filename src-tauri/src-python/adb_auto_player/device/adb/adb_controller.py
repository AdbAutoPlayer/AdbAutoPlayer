import logging
import re
from time import sleep

from adb_auto_player.decorators import register_cache
from adb_auto_player.exceptions import GameStartError, GenericAdbUnrecoverableError
from adb_auto_player.models.decorators import CacheGroup
from adb_auto_player.models.device import DisplayInfo, Orientation, Resolution
from adb_auto_player.models.geometry import Coordinates
from adb_auto_player.tauri_context import profile_aware_cache

from .adb_device import AdbDeviceWrapper


class AdbController:
    """Functions to control an ADB device."""

    d: AdbDeviceWrapper

    def __init__(self):
        """Init."""
        self.d = AdbDeviceWrapper.create_from_settings()
        # Physical display id (for `screencap -d`) and WM logical display id (for
        # `input -d`) of the display hosting the game, resolved lazily on first use.
        # See `_resolve_display_ids`.
        self._screenshot_display_id: str | None = None
        self._input_display_id: str | None = None
        self._display_ids_resolved: bool = False

    def set_display_size(self, display_size: str) -> None:
        """Set display size.

        Args:
            display_size: format width x height e.g. 1080x1920
        """
        _ = self.d.shell(f"wm size {display_size}")
        logging.info(f"Set Display Size to {display_size} for Device: {self.d.serial}")
        self.get_display_info.cache_clear()

    @register_cache(CacheGroup.ADB)
    @profile_aware_cache(maxsize=1)
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

        return DisplayInfo(
            resolution=Resolution.from_string(resolution_str),
            orientation=_check_orientation(self.d),
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

    def screenshot(self, package_name_prefixes: list[str] | None = None) -> str | bytes:
        """Take screenshot.

        Args:
            package_name_prefixes: Prefixes identifying the game's Android package.
                Used once (result is cached for this controller's lifetime) to pick the
                right display when the device exposes more than one, e.g. some
                emulators create a separate virtual display per running app and the
                unspecified/default display for `screencap` is not guaranteed to be the
                one actually running the game.
        """
        self._ensure_display_ids_resolved(package_name_prefixes or [])
        return self.d.screenshot(display_id=self._screenshot_display_id)

    @property
    def screenshot_display_id(self) -> str | None:
        """Physical display id resolved by `resolve_display_targeting`, if any.

        Used by `DeviceStream` to pass `screenrecord --display-id`, so streamed
        frames come from the same display `screenshot()` and `tap()`/etc. target.
        """
        return self._screenshot_display_id

    def resolve_display_targeting(self, package_name_prefixes: list[str]) -> None:
        """Resolve and cache display ids up front, before streaming may start.

        `screenshot()` also resolves lazily on first call, but `DeviceStream`
        captures frames independently via `screenrecord` and never calls
        `screenshot()` — so on devices with multiple displays, calling this once
        during game startup (before `DeviceStream` is created) ensures streamed
        frames, screenshots, and input all agree on which display is the game's,
        instead of only screenshots/input being fixed when streaming is off.

        Args:
            package_name_prefixes: Prefixes identifying the game's Android package.
        """
        self._ensure_display_ids_resolved(package_name_prefixes)

    def _ensure_display_ids_resolved(self, package_name_prefixes: list[str]) -> None:
        """Resolve and cache the game's display ids, once, if not already done."""
        if self._display_ids_resolved:
            return
        self._screenshot_display_id, self._input_display_id = self._resolve_display_ids(
            package_name_prefixes
        )
        self._display_ids_resolved = True

    def _resolve_display_ids(
        self, package_name_prefixes: list[str]
    ) -> tuple[str | None, str | None]:
        """Find the display currently hosting the game.

        Only relevant on devices/emulators that expose more than one display; on a
        normal single-display device this returns (None, None) immediately. Needed
        because on multi-display devices/emulators (observed on MuMuPlayer's Android
        15 image) neither `screencap` nor `input` reliably default to the display
        actually running the game: `screencap` may capture an unrelated idle display,
        and `input` follows whichever display currently has system input focus, which
        can drift to a different display (e.g. the home screen) mid-session.

        Returns:
            tuple[str | None, str | None]: (physical display id for `screencap -d`,
                WM logical display id for `input -d`), or (None, None) to fall back to
                adb's defaults.
        """
        display_output = self.d.shell("dumpsys display")
        if not isinstance(display_output, str):
            return None, None

        # e.g. "displayId=2, uniqueId='local:4619827767814508545'"
        viewports = re.findall(
            r"displayId=(\d+), uniqueId='local:(\d+)'", display_output
        )
        if len(viewports) <= 1 or not package_name_prefixes:
            return None, None
        wm_id_to_physical_id = dict(viewports)

        window_output = self.d.shell("dumpsys window displays")
        if not isinstance(window_output, str):
            return None, None

        current_wm_id: str | None = None
        for line in window_output.splitlines():
            display_match = re.match(r"\s*Display:\s*mDisplayId=(\d+)", line)
            if display_match:
                current_wm_id = display_match.group(1)
                continue
            if (
                current_wm_id is not None
                and "visible=true" in line
                and any(prefix in line for prefix in package_name_prefixes)
            ):
                physical_id = wm_id_to_physical_id.get(current_wm_id)
                if physical_id:
                    logging.info(
                        "Multiple displays detected, targeting display "
                        f"{current_wm_id} (physical id {physical_id}) for "
                        "screenshots and input"
                    )
                    return physical_id, current_wm_id

        return None, None

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
        self.d.tap(
            str(coordinates.x), str(coordinates.y), display_id=self._input_display_id
        )

    def click(
        self,
        coordinates: Coordinates,
    ) -> None:
        """Alias for tap."""
        self.tap(coordinates)

    def press_back_button(self) -> None:
        """Presses the back button."""
        self.d.keyevent("4", display_id=self._input_display_id)  # alternative 111

    def press_enter(self) -> None:
        """Press enter button."""
        self.d.keyevent("66", display_id=self._input_display_id)  # alternative 108

    def swipe(
        self,
        start_point: Coordinates,
        end_point: Coordinates,
        duration: float = 1.0,
    ) -> None:
        """Swipes the screen.

        Args:
            start_point: Start Point on the screen.
            end_point: End Point on the screen.
            duration: Swipe duration in seconds. Defaults to 1.0.
        """
        self.d.swipe(
            str(start_point.x),
            str(start_point.y),
            str(end_point.x),
            str(end_point.y),
            str(int(duration * 1000)),
            display_id=self._input_display_id,
        )

    def hold(
        self,
        coordinates: Coordinates,
        duration: float = 1.0,
    ) -> None:
        """Hold the screen on the given coordinates."""
        self.hold_down(coordinates)
        sleep(duration)
        self.hold_release(coordinates)

    def hold_down(self, coordinates: Coordinates) -> None:
        """Press down at the given coordinates."""
        self.d.shell(self._motion_event_cmd("DOWN", coordinates))

    def hold_release(self, coordinates: Coordinates) -> None:
        """Release touch at the given coordinates."""
        self.d.shell(self._motion_event_cmd("UP", coordinates))

    def _motion_event_cmd(self, action: str, coordinates: Coordinates) -> str:
        display_flag = f"-d {self._input_display_id} " if self._input_display_id else ""
        coords = coordinates.as_adb_shell_str()
        return f"input {display_flag}motionevent {action} {coords}"

    @property
    @register_cache(CacheGroup.ADB)
    @profile_aware_cache(maxsize=1)
    def is_controlling_emulator(self):
        """Whether the controlled device is an emulator or not."""
        result = str(self.d.shell('getprop | grep "Build"'))
        if "Build" in result:
            return True
        logging.debug('getprop does not contain "Build" assuming Phone')
        return False

    def get_input_device(self, name: str) -> str | None:
        """Return /dev/input/eventX for a given input device name."""
        content = _get_input_devices(self.d)
        blocks = content.strip().split("\n\n")
        for block in blocks:
            if f'N: Name="{name}"' in block:
                match = re.search(r"Handlers=.*?(event\d+)", block)
                if match:
                    return f"/dev/input/{match.group(1)}"
        return None


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


def _get_input_devices(d: AdbDeviceWrapper) -> str:
    """Return full /proc/bus/input/devices contents."""
    return d.shell("cat /proc/bus/input/devices")
