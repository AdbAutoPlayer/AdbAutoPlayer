"""Screenshot and device-stream mixin."""

import logging
import sys
from time import sleep

import numpy as np
from adb_auto_player.device.adb import DeviceStream
from adb_auto_player.exceptions import (
    AutoPlayerWarningError,
    GenericAdbUnrecoverableError,
    UnsupportedResolutionError,
)
from adb_auto_player.file_loader import SettingsLoader
from adb_auto_player.image_manipulation import IO, Color
from adb_auto_player.models.device import Resolution

from ._base import _GameBase


class _ScreenshotMixin(_GameBase):
    """Mixin providing screenshot capture and H264 device-stream management."""

    def start_stream(self) -> None:
        """Start the H264 device stream."""
        try:
            self._stream = DeviceStream(self.device)
        except AutoPlayerWarningError as e:
            logging.warning(f"{e}")

        if self._stream is None:
            return

        self._stream.start()
        time_waiting = 0
        attempts = 10
        while True:
            if time_waiting >= attempts:
                logging.error("Could not start Device Stream using screenshots instead")
                if self._stream:
                    self._stream.stop()
                    self._stream = None
                break
            if self._stream and self._stream.get_latest_frame() is not None:
                logging.debug("Device Stream started")
                break
            sleep(1)
            time_waiting += 1

    def stop_stream(self) -> None:
        """Stop the H264 device stream."""
        if self._stream:
            self._stream.stop()
            self._stream = None

    def get_screenshot(self) -> np.ndarray:
        """Get a screenshot from the device (stream-first, fallback screencap).

        Returns:
            np.ndarray: BGR screenshot.

        Raises:
            GenericAdbUnrecoverableError: Screenshot cannot be captured.
        """
        if self._stream:
            image = self._stream.get_latest_frame()
            if image is not None:
                return Color.to_bgr(image)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                data = self.device.screenshot()
                if isinstance(data, bytes):
                    return IO.get_bgr_np_array_from_png_bytes(data)
            except (OSError, ValueError) as e:
                logging.debug(
                    f"Attempt {attempt + 1}/{max_retries}: "
                    f"Failed to process screenshot: {e}"
                )
                sleep(0.1)

        raise GenericAdbUnrecoverableError(
            f"Screenshots cannot be recorded from device: {self.device.identifier}"
        )

    def _check_screenshot_matches_display_resolution(
        self, device_streaming_check: bool = False
    ) -> None:
        height, width = self.get_screenshot().shape[:2]
        if (width, height) != self.display_info.dimensions:
            if device_streaming_check:
                logging.warning(
                    f"Device Stream resolution ({width}, {height}) "
                    f"does not match Display Resolution {self.display_info}, "
                    "stopping Device Streaming"
                )
                self.stop_stream()
                return
            logging.error(
                f"Screenshot resolution ({width}, {height}) "
                f"does not match Display Resolution {self.display_info}, "
                "exiting..."
            )
            sys.exit(1)

    def _set_device_resolution(self) -> None:
        if not SettingsLoader.adb_settings().device.use_wm_resize:
            return
        if not self.base_resolution == self.display_info.normalized_resolution:
            self.device.set_display_size(str(self.base_resolution))

    def _check_requirements(self) -> None:
        """Validate device resolution and orientation.

        Raises:
            UnsupportedResolutionError: Device resolution is not supported.
        """
        current: Resolution = self.display_info.normalized_resolution
        base: Resolution = self.base_resolution

        if base == current:
            return

        msg = f"This bot only supports: {base} resolution, detected: {current}"

        if (
            base.orientation == self.display_info.orientation
            or base.is_square
            or current.is_square
        ):
            raise UnsupportedResolutionError(msg)

        orientation_hint = "Portrait" if base.is_portrait else "Landscape"
        raise UnsupportedResolutionError(
            f"{msg} and must be in {orientation_hint} orientation: "
            "https://AdbAutoPlayer.github.io/AdbAutoPlayer/user-guide/"
            "troubleshoot.html#this-bot-only-works-in-portrait-mode"
        )

    def _start_device_streaming(self, device_streaming: bool = True) -> None:
        if not device_streaming:
            if self._stream:
                logging.debug("Stopping device streaming")
                self._stream.stop()
            return

        if self._stream:
            logging.debug("Device stream already started")
            return

        if not SettingsLoader.adb_settings().device.streaming:
            logging.warning("Real-time Display Streaming is disabled in ADB Settings")
            return

        self.start_stream()
        self._check_screenshot_matches_display_resolution(device_streaming_check=True)
