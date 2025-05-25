"""Android Debug Bridge Interaction Module."""

from __future__ import annotations

import logging
import re
import time
from typing import TYPE_CHECKING, Any

from ...exception.exceptions import InteractionFailedError
from ...connection.base import Connection
from ..base import Interaction
from ..models import Coordinates, InteractionWait, KeyEvent

if TYPE_CHECKING:
    from ...connection.adbutils.connection import AdbUtilsConnection


logger = logging.getLogger(__name__)


class AdbUtilsInteraction(Interaction):
    """Manages device interactions using the adbutils library via shell commands."""

    def __init__(self, connection: Connection) -> None:
        """
        Initialize the ADB interaction manager.

        Args:
            connection: An instance of a Connection (expected to be AdbUtilsConnection).
        """
        super().__init__(connection)

        if not hasattr(connection, "execute_shell_command"):
            msg = "AdbUtilsInteraction requires a connection object with 'execute_shell_command' method."
            logger.error(msg)
            raise TypeError(msg)
        self._adb_connection: AdbUtilsConnection = connection  # type: ignore[assignment]

    def _execute_interaction_command(
        self, command: str, wait: InteractionWait | None = None, timeout: int | None = 5
    ) -> str:
        """
        Execute an interaction command and handle optional waits.

        Args:
            command: The ADB shell command to execute.
            wait: Optional wait times before and after the interaction.
            timeout: Timeout for the shell command execution.

        Returns:
            The output of the command.

        Raises:
            InteractionFailedError: If the command execution fails or returns no output
                                    when output is expected for parsing.
        """
        if wait and wait.before > 0:
            logger.debug("Waiting %s seconds before interaction.", wait.before)
            time.sleep(wait.before)

        logger.debug("Executing interaction command: %s", command)
        try:
            result = self._adb_connection.execute_shell_command(command, timeout=timeout)

            if result is None:  # Should not happen based on AdbUtilsConnection's current return type
                logger.warning("Interaction command '%s' returned None unexpectedly.", command)
                raise InteractionFailedError(f"Command '{command}' returned None.")
            return str(result)
        except Exception as e:
            msg = f"Failed to execute interaction command '{command}': {e}"
            logger.error(msg)
            raise InteractionFailedError(msg) from e
        finally:
            if wait and wait.after > 0:
                logger.debug("Waiting %s seconds after interaction.", wait.after)
                time.sleep(wait.after)

    def _handle_coordinates_interaction(
        self, target: Coordinates, wait: InteractionWait | None = None, **kwargs: Any
    ) -> None:
        """
        Handle interaction with a single coordinate (tap).

        Args:
            target: The Coordinates object representing the tap location.
            wait: Optional wait times before and after the interaction.
            **kwargs: Additional keyword arguments (not used in this handler).
        """
        command = f"input tap {target.x} {target.y}"
        self._execute_interaction_command(command, wait)
        logger.info("Tapped at coordinates: %s", target)

    def _handle_coordinate_pair_interaction(
        self,
        target: tuple[Coordinates, Coordinates],
        wait: InteractionWait | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Handle interaction with a pair of coordinates (swipe).

        Args:
            target: A tuple containing start and end Coordinates for the swipe.
            wait: Optional wait times before and after the interaction.
            **kwargs: Supports 'duration_ms' for swipe duration.
        """
        start_coords, end_coords = target
        duration_ms = kwargs.get("duration_ms")
        command = f"input swipe {start_coords.x} {start_coords.y} {end_coords.x} {end_coords.y}"
        if duration_ms:
            try:
                command += f" {int(duration_ms)}"
            except ValueError:
                logger.warning("Invalid duration_ms '%s' for swipe, ignoring.", duration_ms)

        self._execute_interaction_command(command, wait)
        logger.info(
            "Swiped from %s to %s%s",
            start_coords,
            end_coords,
            f" with duration {duration_ms}ms" if duration_ms else "",
        )

    def _handle_text_interaction(
        self, target: str, wait: InteractionWait | None = None, **kwargs: Any
    ) -> None:
        """
        Handle text input interaction.

        Args:
            target: The text string to input.
            wait: Optional wait times before and after the interaction.
            **kwargs: Additional keyword arguments (not used in this handler).
        """
        # ADB 'input text' requires careful escaping for shell.
        # Replace single quotes with '\\'' and wrap the whole string in single quotes.
        escaped_text = target.replace("'", "'\\\\''")
        command = f"input text '{escaped_text}'"
        self._execute_interaction_command(command, wait)
        logger.info("Input text (first 20 chars): '%s...'", target[:20])

    def _handle_key_event_interaction(
        self, target: KeyEvent, wait: InteractionWait | None = None, **kwargs: Any
    ) -> None:
        """
        Handle key event interaction.

        Args:
            target: The KeyEvent object representing the key event.
            wait: Optional wait times before and after the interaction.
            **kwargs: Additional keyword arguments (not used in this handler).
        """
        command = f"input keyevent {target.identifier}"
        self._execute_interaction_command(command, wait)
        logger.info("Sent key event: %s", target.identifier)

    def get_screen_resolution(self) -> Coordinates | None:
        """
        Get the device screen resolution.

        Returns:
            A Coordinates object (x=width, y=height) representing physical size,
            adjusted for portrait orientation, or None if an error occurs.
            The old code returned physical_size if override_size was not present,
            and adjusted it if not in portrait.
        """
        try:
            output = self._execute_interaction_command("wm size")
        except InteractionFailedError as e:
            logger.error("Failed to get screen resolution: %s", e)
            return None

        physical_size_match = re.search(r"Physical size: (\d+x\d+)", output)
        override_size_match = re.search(r"Override size: (\d+x\d+)", output)

        resolution_str: str | None = None
        if override_size_match:
            resolution_str = override_size_match.group(1)
            logger.debug("Using override screen size: %s", resolution_str)
        elif physical_size_match:
            resolution_str = physical_size_match.group(1)
            logger.debug("Using physical screen size: %s", resolution_str)

        if not resolution_str:
            logger.error("Could not parse screen resolution from 'wm size' output: %s", output)
            return None

        try:
            width_str, height_str = resolution_str.split("x")
            width, height = int(width_str), int(height_str)

            if not self.is_portrait():
                logger.debug("Device is in landscape, swapping width/height for resolution.")
                return Coordinates(x=height, y=width)
            return Coordinates(x=width, y=height)
        except ValueError as e:
            logger.error("Failed to parse width/height from resolution string '%s': %s", resolution_str, e)
            return None
        except InteractionFailedError as e:
            logger.warning("Failed to determine orientation for screen resolution, returning as is: %s", e)
            # Fallback to returning parsed resolution without orientation adjustment
            if 'width' in locals() and 'height' in locals():
                return Coordinates(x=width, y=height)  # type: ignore[possibly-undefined]
            return None

    def set_screen_resolution(self, width: int, height: int) -> None:
        """
        Sets the display size to the given resolution using 'wm size <width>x<height>'.

        Args:
            width: The target width.
            height: The target height.

        Raises:
            InteractionFailedError: If the command fails.
        """
        command = f"wm size {width}x{height}"
        try:
            output = self._execute_interaction_command(command)
            if "java.lang.SecurityException" in output:
                msg = "Permission denied for 'wm size'. Check developer options for 'Disable permission monitoring' or similar."
                logger.error(msg)
                raise InteractionFailedError(msg)
            logger.info("Set screen resolution to %dx%d.", width, height)
        except InteractionFailedError as e:
            logger.error("Failed to set screen resolution to %dx%d: %s", width, height, e)
            raise

    def reset_screen_resolution(self) -> None:
        """
        Resets the display size of the device to its original physical size using 'wm size reset'.

        Raises:
            InteractionFailedError: If the command fails.
        """
        command = "wm size reset"
        try:
            self._execute_interaction_command(command)
            logger.info("Reset screen resolution to physical.")
        except InteractionFailedError as e:
            logger.error("Failed to reset screen resolution: %s", e)
            raise

    def is_portrait(self) -> bool:
        """
        Check if the device is in portrait orientation.
        This replicates the logic from the old adb.py which checked multiple dumpsys outputs.
        Defaulting to True if checks are inconclusive or fail, as per old behavior implicit in `all(checks)`.

        Returns:
            True if determined to be in portrait, False for landscape.
            Defaults to True if checks fail or are ambiguous.
        """
        surface_orientation_val: int | None = None
        try:
            orientation_check_output = self._execute_interaction_command(
                "dumpsys input | grep 'SurfaceOrientation'"
            )
            match = re.search(r"SurfaceOrientation:\s*(\d+)", orientation_check_output)
            if match:
                surface_orientation_val = int(match.group(1))
                logger.debug("SurfaceOrientation: %s", surface_orientation_val)
            else:
                logger.warning("Could not parse SurfaceOrientation from: %s", orientation_check_output)
        except InteractionFailedError as e:
            logger.warning("Failed to get SurfaceOrientation: %s. Proceeding with other checks.", e)
        except ValueError:
            logger.warning("Invalid value for SurfaceOrientation. Proceeding...")

        current_rotation_portrait: bool | None = None
        try:
            rotation_check_output = self._execute_interaction_command(
                "dumpsys window | grep -E 'mCurrentRotation|mDisplayRotation'"  # mDisplayRotation is a fallback
            )

            if "ROTATION_0" in rotation_check_output or "ROTATION_180" in rotation_check_output:
                current_rotation_portrait = True
            elif "ROTATION_90" in rotation_check_output or "ROTATION_270" in rotation_check_output:
                current_rotation_portrait = False
            logger.debug("mCurrentRotation check implies portrait: %s", current_rotation_portrait)
            if current_rotation_portrait is None:
                logger.warning("Could not determine portrait from mCurrentRotation: %s", rotation_check_output)
        except InteractionFailedError as e:
            logger.warning("Failed to get mCurrentRotation: %s. Proceeding with other checks.", e)

        display_orientation_portrait: bool | None = None
        try:
            display_check_output = self._execute_interaction_command(
                "dumpsys display | grep -E 'orientation='"  # Look for lines like 'orientation=0'
            )

            if re.search(r"orientation=0", display_check_output) or \
               re.search(r"orientation=2", display_check_output):
                display_orientation_portrait = True
            elif re.search(r"orientation=1", display_check_output) or \
                 re.search(r"orientation=3", display_check_output):
                display_orientation_portrait = False  # Explicitly landscape
            logger.debug("Display orientation check implies portrait: %s", display_orientation_portrait)
            if display_orientation_portrait is None:
                logger.warning("Could not determine portrait from display orientation: %s", display_check_output)

        except InteractionFailedError as e:
            logger.warning("Failed to get display orientation: %s.", e)

        if surface_orientation_val is not None:
            is_p = surface_orientation_val in (0, 2)
            logger.debug("Using SurfaceOrientation for portrait decision: %s", is_p)
            return is_p

        if current_rotation_portrait is not None:
            logger.debug("Using mCurrentRotation for portrait decision: %s", current_rotation_portrait)
            return current_rotation_portrait

        if display_orientation_portrait is not None:
            logger.debug("Using display orientation for portrait decision: %s", display_orientation_portrait)
            return display_orientation_portrait

        logger.warning("Could not definitively determine orientation. Defaulting to True (portrait).")
        return True

    def get_current_app_package(self) -> str | None:
        """
        Get the package name of the currently focused application.
        Replicates the logic from the old adb.py's get_running_app.

        Returns:
            The package name string (e.g., "com.example.app") or None if not found.
        """
        commands_to_try = [
            "dumpsys activity activities | grep -E 'mResumedActivity|ResumedActivity'",  # Primary
            "dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'"  # Fallback
        ]
        # Regex to find <package>/<activity> or <package>/.<activity>
        app_pattern = re.compile(r"([a-zA-Z0-9._-]+)/[.a-zA-Z0-9._-]+")

        for cmd in commands_to_try:
            try:
                output = self._execute_interaction_command(cmd, timeout=10)
                if not output:
                    continue

                # Search for the pattern in each line of the output
                for line in output.splitlines():
                    match = app_pattern.search(line)
                    if match:
                        package_name = match.group(1)
                        if package_name:
                            logger.debug("Found current app package: %s (from command: %s)", package_name, cmd)
                            return package_name
            except InteractionFailedError as e:
                logger.warning("Command '%s' failed while getting current app: %s", cmd, e)
            except Exception as e:
                logger.error("Error parsing output for command '%s': %s", cmd, e, exc_info=True)

        logger.warning("Could not determine current app package.")
        return None
