"""ADB Auto Player Game Base Module."""

import logging
import os
import sys
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum, auto
from pathlib import Path
from time import sleep, time
from typing import Literal, TypeVar

import cv2
import numpy as np
from adb_auto_player.device.adb import AdbController, DeviceStream
from adb_auto_player.exceptions import (
    AutoPlayerError,
    AutoPlayerUnrecoverableError,
    AutoPlayerWarningError,
    GameActionFailedError,
    GameNotRunningOrFrozenError,
    GameTimeoutError,
    GenericAdbUnrecoverableError,
    UnsupportedResolutionError,
)
from adb_auto_player.image_manipulation import (
    IO,
    Color,
    Cropping,
)
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.device import DisplayInfo, Orientation
from adb_auto_player.models.geometry import Coordinates, Point, PointOutsideDisplay
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.models.pydantic import MyCustomRoutineConfig
from adb_auto_player.models.registries import CustomRoutineEntry
from adb_auto_player.models.template_matching import MatchMode, TemplateMatchResult
from adb_auto_player.registries import CUSTOM_ROUTINE_REGISTRY
from adb_auto_player.settings import ConfigLoader
from adb_auto_player.template_matching import TemplateMatcher
from adb_auto_player.util import Execute, StringHelper
from PIL import Image
from pydantic import BaseModel


class _SwipeDirection(StrEnum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()

    @property
    def is_vertical(self) -> bool:
        """Return True if the direction is vertical (UP or DOWN)."""
        return self in {_SwipeDirection.UP, _SwipeDirection.DOWN}

    @property
    def is_increasing(self) -> bool:
        """Return True if the coordinate increases in the direction (DOWN or RIGHT)."""
        return self in {_SwipeDirection.DOWN, _SwipeDirection.RIGHT}


@dataclass
class _SwipeParams:
    direction: _SwipeDirection
    x: int | None = None
    y: int | None = None
    start: int | None = None
    end: int | None = None
    duration: float = 1.0


class Game(ABC):
    """Generic Game class."""

    def __init__(self) -> None:
        """Initialize a game."""
        self.config: BaseModel | None = None
        self.default_threshold: ConfidenceValue = ConfidenceValue("90%")
        self.disable_debug_screenshots: bool = False

        self.package_name_substrings: list[str] = []
        self.package_name: str | None = None
        self.supports_landscape: bool = False
        self.supports_portrait: bool = False
        self.supported_resolutions: list[str] = ["1080x1920"]

        self._config_file_path: Path | None = None
        self._debug_screenshot_counter: int = 0
        self._device: AdbController | None = None
        self._scale_factor: float | None = None
        self._stream: DeviceStream | None = None
        self._template_dir_path: Path | None = None

    @abstractmethod
    def _load_config(self):
        """Required method to load the game configuration."""
        ...

    @abstractmethod
    def get_config(self) -> BaseModel:
        """Required method to return the game configuration."""
        ...

    @property
    def scale_factor(self) -> float:
        """Get the scale factor of the current resolution relative to a reference.

        The reference resolution is (1080, 1920) and the scale factor is the width of
        the current resolution divided by the width of the reference resolution.

        The scale factor is used to scale the coordinates of templates and is used by
        `get_templates` to get the correct size of templates.

        Returns:
            float: Scale factor of the current resolution.
        """
        if self._scale_factor:
            return self._scale_factor

        resolution_str = self.supported_resolutions[0]
        width, height = map(int, resolution_str.split("x"))
        reference_resolution = (width, height)
        if self.display_info.dimensions == reference_resolution:
            self._scale_factor = 1.0
        else:
            self._scale_factor = self.display_info.width / reference_resolution[0]
        logging.debug(f"scale_factor: {self._scale_factor}")
        return self._scale_factor

    @property
    def display_info(self) -> DisplayInfo:
        """Resolves and returns DisplayInfo instance."""
        return self.device.get_display_info()

    @property
    def device(self) -> AdbController:
        """Get device."""
        if self._device is None:
            self._device = AdbController()
        return self._device

    def start_stream(self) -> None:
        """Start the device stream."""
        try:
            self._stream = DeviceStream(
                self.device,
            )
        except AutoPlayerWarningError as e:
            logging.warning(f"{e}")

        if self._stream is None:
            return

        self._stream.start()
        time_waiting_for_stream_to_start = 0
        attempts = 10
        while True:
            if time_waiting_for_stream_to_start >= attempts:
                logging.error("Could not start Device Stream using screenshots instead")
                if self._stream:
                    self._stream.stop()
                    self._stream = None
                break
            if self._stream and self._stream.get_latest_frame() is not None:
                logging.debug("Device Stream started")
                break
            sleep(1)
            time_waiting_for_stream_to_start += 1

    def stop_stream(self):
        """Stop the device stream."""
        if self._stream:
            self._stream.stop()
            self._stream = None

    def open_eyes(self, device_streaming: bool = True) -> None:
        """Give the bot eyes.

        Set the device for the game and start the device stream.

        Args:
            device_streaming (bool, optional): Whether to start the device stream.
        """
        self._set_device_resolution()
        self._check_requirements()

        self._start_device_streaming(device_streaming=device_streaming)
        self._check_screenshot_matches_display_resolution(device_streaming_check=False)

        if self.is_game_running():
            return

        if not self.package_name:
            raise GameNotRunningOrFrozenError("Game is not running, exiting...")

        logging.warning("Game is not running, trying to start the game.")
        self.start_game()
        if not self.is_game_running():
            raise GameNotRunningOrFrozenError("Game could not be started, exiting...")
        return

    def _start_device_streaming(self, device_streaming: bool = True) -> None:
        if self._stream and not device_streaming:
            logging.debug("Stopping device streaming")
            self._stream.stop()
            return

        if self._stream:
            logging.debug("Device stream already started")
            return

        if device_streaming:
            if not ConfigLoader.general_settings().device.streaming:
                logging.warning("Device Streaming is disabled in General Settings")
                return

            self.start_stream()
            self._check_screenshot_matches_display_resolution(
                device_streaming_check=True
            )
        return

    def _set_device_resolution(self):
        if not ConfigLoader.general_settings().device.use_wm_resize:
            return

        suggested_resolution: str | None = next(
            (res for res in self.supported_resolutions if "x" in res), None
        )
        if (
            suggested_resolution
            and suggested_resolution != self.display_info.resolution
        ):
            self.device.set_display_size(suggested_resolution)
        return

    def _is_supported_resolution(self) -> bool:
        """Return True if the resolution is supported."""
        width = self.display_info.width
        height = self.display_info.height
        for supported_resolution in self.supported_resolutions:
            if "x" in supported_resolution:
                res_width, res_height = map(int, supported_resolution.split("x"))
                if res_width == width and res_height == height:
                    return True
            elif ":" in supported_resolution:
                aspect_width, aspect_height = map(int, supported_resolution.split(":"))
                if width * aspect_height == height * aspect_width:
                    return True
        return False

    def _check_requirements(self) -> None:
        """Validates Device properties such as resolution and orientation.

        Raises:
             UnsupportedResolutionException: Device resolution is not supported.
        """
        if not self._is_supported_resolution():
            raise UnsupportedResolutionError(
                "This bot only supports these resolutions: "
                f"{', '.join(self.supported_resolutions)}"
            )

        if (
            self.supports_portrait
            and not self.supports_landscape
            and self.display_info.orientation == Orientation.LANDSCAPE
        ):
            raise UnsupportedResolutionError(
                "This bot only works in Portrait mode: "
                "https://AdbAutoPlayer.github.io/AdbAutoPlayer/user-guide/"
                "troubleshoot.html#this-bot-only-works-in-portrait-mode"
            )

        if (
            self.supports_landscape
            and not self.supports_portrait
            and self.display_info.orientation == Orientation.PORTRAIT
        ):
            raise UnsupportedResolutionError(
                "This bot only works in Landscape mode: "
                "https://AdbAutoPlayer.github.io/AdbAutoPlayer/user-guide/"
                "troubleshoot.html#this-bot-only-works-in-portrait-mode"
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
                f"exiting..."
            )
            sys.exit(1)
        return

    def tap(
        self,
        coordinates: Coordinates,
        scale: bool = False,
        blocking: bool = True,
        # Assuming 30 FPS, 1 Tap per Frame
        non_blocking_sleep_duration: float | None = 1 / 30,
        log_message: str | None = None,
        log: bool = True,
    ) -> None:
        """Tap the screen on the given point.

        Args:
            coordinates (Coordinates): Point to click on.
            scale (bool, optional): Whether to scale the coordinates.
            blocking (bool, optional): Whether to block the process and
                wait for ADBServer to confirm the tap has happened.
            non_blocking_sleep_duration (float, optional): Sleep time in seconds for
                non-blocking taps, needed to not DoS the ADBServer.
            log_message (str | None, optional): Custom Log message, default msg if None
            log (bool, optional): Log the tap command.
        """
        original_point = coordinates
        final_point = coordinates

        if scale:
            final_point = Point(coordinates.x, coordinates.y).scale(self._scale_factor)

        if log:
            log_message = Game._build_tap_log_message(
                original_point,
                final_point,
                log_message,
            )
        else:
            log_message = None

        # Perform the tap
        if blocking:
            self._click(
                final_point,
                log_message,
            )
        else:
            thread = threading.Thread(
                target=self._click,
                args=(
                    final_point,
                    log_message,
                ),
                daemon=True,
            )
            thread.start()
            if non_blocking_sleep_duration is not None:
                sleep(non_blocking_sleep_duration)

    @staticmethod
    def _build_tap_log_message(
        original_point: Coordinates,
        final_point: Coordinates,
        message: str | None = None,
    ) -> str | None:
        """Log the tap with all relevant information in a single entry."""
        if message is None:
            return None

        coords_info = (
            f"{original_point} (scaled to {final_point})"
            if original_point != final_point
            else str(final_point)
        )

        if message:
            return f"{message}: {coords_info}"
        return f"Tapped: {coords_info}"

    def _click(
        self,
        coordinates: Coordinates,
        log_message: str | None = None,
    ) -> None:
        """Internal click method - logging should typically be handled by the caller."""
        self.device.tap(coordinates)
        if log_message is not None:
            logging.debug(log_message)

    def get_screenshot(self) -> np.ndarray:
        """Gets screenshot from device using stream or screencap.

        Raises:
            AdbException: Screenshot cannot be recorded
        """
        if self._stream:
            image = self._stream.get_latest_frame()
            if image is not None:
                self._debug_save_screenshot(image, is_bgr=False)
                return Color.to_bgr(image)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                data = self.device.screenshot()
                if isinstance(data, bytes):
                    image = IO.get_bgr_np_array_from_png_bytes(data)
                    self._debug_save_screenshot(image, is_bgr=True)
                    return image
            except (OSError, ValueError) as e:
                logging.debug(
                    f"Attempt {attempt + 1}/{max_retries}: "
                    f"Failed to process screenshot: {e}"
                )
                sleep(0.1)

        raise GenericAdbUnrecoverableError(
            f"Screenshots cannot be recorded from device: {self.device.identifier}"
        )

    def force_stop_game(self):
        """Force stops the Game."""
        if not self.package_name:
            return
        self.device.stop_game(self.package_name)

    def is_game_running(self) -> bool:
        """Check if Game is still running."""
        package_name = self.device.get_running_app()
        if package_name is None:
            return False

        if any(pn in package_name for pn in self.package_name_substrings):
            self.package_name = package_name
            return True

        return package_name == self.package_name

    def start_game(self) -> None:
        """Start the Game.

        Raises:
            GameStartError: Game cannot be started.
        """
        if not self.package_name:
            return
        self.device.start_game(self.package_name)

    def wait_for_roi_change(
        self,
        start_image: np.ndarray,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        delay: float = 0.5,
        timeout: float = 30,
        timeout_message: str | None = None,
    ) -> bool:
        """Waits for a region of interest (ROI) on the screen to change.

        This function monitors a specific region of the screen defined by
        the crop values.
        If the crop values are all set to 0, it will monitor the entire
        screen for changes.
        A change is detected based on a similarity threshold between current and
        previous screen regions.

        Args:
            start_image (np.ndarray): Image to start monitoring.
            threshold (float): Similarity threshold. Defaults to 0.9.
            grayscale (bool): Whether to convert images to grayscale before comparison.
                Defaults to False.
            crop_regions (CropRegions): Crop percentages for trimming the image.
            delay (float): Delay between checks in seconds. Defaults to 0.5.
            timeout (float): Timeout in seconds. Defaults to 30.
            timeout_message (str | None): Custom timeout message. Defaults to None.

        Returns:
            bool: True if the region of interest has changed, False otherwise.

        Raises:
            TimeoutException: If no change is detected within the timeout period.
            ValueError: Invalid crop values.
        """
        crop_result = Cropping.crop(image=start_image, crop_regions=crop_regions)

        def roi_changed() -> Literal[True] | None:
            inner_crop_result = Cropping.crop(
                image=self.get_screenshot(),
                crop_regions=crop_regions,
            )

            result = not TemplateMatcher.similar_image(
                base_image=crop_result.image,
                template_image=inner_crop_result.image,
                threshold=threshold or self.default_threshold,
                grayscale=grayscale,
            )

            if result:
                return True
            return None

        if timeout_message is None:
            timeout_message = (
                f"Region of Interest has not changed after {timeout} seconds"
            )

        return self._execute_or_timeout(
            roi_changed, delay=delay, timeout=timeout, timeout_message=timeout_message
        )

    # TODO: Change this function name.
    # It is the same as template_matching.find_template_match
    def game_find_template_match(
        self,
        template: str | Path,
        match_mode: MatchMode = MatchMode.BEST,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        screenshot: np.ndarray | None = None,
    ) -> TemplateMatchResult | None:
        """Find a template on the screen.

        Args:
            template (str | Path): Path to the template image.
            match_mode (MatchMode, optional): Defaults to MatchMode.BEST.
            threshold (ConfidenceValue, optional): Image similarity threshold.
            grayscale (bool, optional): Convert to grayscale boolean. Defaults to False.
            crop_regions (CropRegions, optional): Crop percentages.
            screenshot (np.ndarray, optional): Screenshot image. Will fetch screenshot
                if None

        Returns:
            TemplateMatchResult | None
        """
        crop_result = Cropping.crop(
            image=screenshot if screenshot is not None else self.get_screenshot(),
            crop_regions=crop_regions,
        )

        match = TemplateMatcher.find_template_match(
            base_image=crop_result.image,
            template_image=self._load_image(
                template=template,
                grayscale=grayscale,
            ),
            match_mode=match_mode,
            threshold=threshold or self.default_threshold,
            grayscale=grayscale,
        )

        if match is None:
            return None

        return match.with_offset(crop_result.offset).to_template_match_result(
            template=str(template)
        )

    def _load_image(
        self,
        template: str | Path,
        grayscale: bool = False,
    ) -> np.ndarray:
        return IO.load_image(
            image_path=self.get_template_dir_path() / template,
            image_scale_factor=self.scale_factor,
            grayscale=grayscale,
        )

    def find_worst_match(
        self,
        template: str | Path,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
    ) -> None | TemplateMatchResult:
        """Find the most different match.

        Args:
            template (str | Path): Path to template image.
            grayscale (bool, optional): Convert to grayscale boolean. Defaults to False.
            crop_regions (CropRegions, optional): Crop percentages.

        Returns:
            None | TemplateMatchResult: None or Result of worst Match.
        """
        crop_result = Cropping.crop(
            image=self.get_screenshot(), crop_regions=crop_regions
        )

        result = TemplateMatcher.find_worst_template_match(
            base_image=crop_result.image,
            template_image=self._load_image(
                template=template,
                grayscale=grayscale,
            ),
            grayscale=grayscale,
        )

        if result is None:
            return None

        return result.with_offset(crop_result.offset).to_template_match_result(
            template=str(template)
        )

    def find_all_template_matches(
        self,
        template: str | Path,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        min_distance: int = 10,
    ) -> list[TemplateMatchResult]:
        """Find all matches.

        Args:
            template (str | Path): Path to template image.
            threshold (float, optional): Image similarity threshold. Defaults to 0.9.
            grayscale (bool, optional): Convert to grayscale boolean. Defaults to False.
            crop_regions (CropRegions, optional): Crop percentages.
            min_distance (int, optional): Minimum distance between matches.
                Defaults to 10.

        Returns:
            list[tuple[int, int]]: List of found coordinates.
        """
        crop_result = Cropping.crop(
            image=self.get_screenshot(), crop_regions=crop_regions
        )

        result = TemplateMatcher.find_all_template_matches(
            base_image=crop_result.image,
            template_image=self._load_image(
                template=template,
                grayscale=grayscale,
            ),
            threshold=threshold or self.default_threshold,
            grayscale=grayscale,
            min_distance=min_distance,
        )

        results: list[TemplateMatchResult] = []
        for match in result:
            results.append(
                match.with_offset(crop_result.offset).to_template_match_result(
                    template=str(template)
                )
            )
        return results

    def wait_for_template(
        self,
        template: str | Path,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        delay: float = 0.5,
        timeout: float = 30,
        timeout_message: str | None = None,
    ) -> TemplateMatchResult:
        """Waits for the template to appear in the screen.

        Raises:
            GameTimeoutError: Template not found.
        """

        def find_template() -> TemplateMatchResult | None:
            result = self.game_find_template_match(
                template,
                threshold=threshold or self.default_threshold,
                grayscale=grayscale,
                crop_regions=crop_regions,
            )
            if result is not None:
                logging.debug(f"wait_for_template: {template} found")
            return result

        if timeout_message is None:
            timeout_message = (
                f"Could not find Template: '{template}' after {timeout} seconds"
            )

        return self._execute_or_timeout(
            find_template, delay=delay, timeout=timeout, timeout_message=timeout_message
        )

    def wait_until_template_disappears(
        self,
        template: str | Path,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        delay: float = 0.5,
        timeout: float = 30,
        timeout_message: str | None = None,
    ) -> None:
        """Waits for the template to disappear from the screen.

        Raises:
            TimeoutException: Template still visible.
        """

        def find_best_template() -> TemplateMatchResult | None:
            result: TemplateMatchResult | None = self.game_find_template_match(
                template,
                threshold=threshold or self.default_threshold,
                grayscale=grayscale,
                crop_regions=crop_regions,
            )
            if result is None:
                logging.debug(
                    f"wait_until_template_disappears: {template} no longer visible"
                )

            return result

        if timeout_message is None:
            timeout_message = (
                f"Template: {template} is still visible after {timeout} seconds"
            )

        self._execute_or_timeout(
            find_best_template,
            delay=delay,
            timeout=timeout,
            timeout_message=timeout_message,
            result_should_be_none=True,
        )

    def wait_for_any_template(
        self,
        templates: list[str],
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        delay: float = 0.5,
        timeout: float = 30,
        timeout_message: str | None = None,
        ensure_order: bool = True,
    ) -> TemplateMatchResult:
        """Waits for any template to appear on the screen.

        Raises:
            TimeoutException: No template visible.
        """

        def find_template() -> TemplateMatchResult | None:
            return self.find_any_template(
                templates,
                threshold=threshold or self.default_threshold,
                grayscale=grayscale,
                crop_regions=crop_regions,
            )

        if timeout_message is None:
            timeout_message = (
                f"None of the templates {templates} were found after {timeout} seconds"
            )

        result = self._execute_or_timeout(
            find_template, delay=delay, timeout=timeout, timeout_message=timeout_message
        )

        # Should not be needed anymore because find_any_template reuses the screenshot
        # during a single iteration
        if not ensure_order:
            return result

        # this ensures correct order
        # using lower delay and timeout as this function should return without a retry.
        sleep(delay)
        return self._execute_or_timeout(
            find_template, delay=0.5, timeout=3, timeout_message=timeout_message
        )

    def find_any_template(
        self,
        templates: list[str],
        match_mode: MatchMode = MatchMode.BEST,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        screenshot: np.ndarray | None = None,
    ) -> TemplateMatchResult | None:
        """Find any first template on the screen.

        Args:
            templates (list[str]): List of templates to search for.
            match_mode (MatchMode, optional): String enum. Defaults to MatchMode.BEST.
            threshold (float, optional): Image similarity threshold. Defaults to 0.9.
            grayscale (bool, optional): Convert to grayscale boolean. Defaults to False.
            crop_regions (CropRegions, optional): Crop percentages.
            screenshot (np.ndarray, optional): Screenshot image. Will fetch screenshot
                if None
        Returns:
            TemplateMatchResult | None
        """
        screenshot = screenshot if screenshot is not None else self.get_screenshot()

        offset = None
        if crop_regions:
            cropped = Cropping.crop(screenshot, crop_regions)
            screenshot = cropped.image
            offset = cropped.offset

        if grayscale:
            screenshot = Color.to_grayscale(screenshot)

        for template in templates:
            result = self.game_find_template_match(
                template,
                match_mode=match_mode,
                threshold=threshold or self.default_threshold,
                screenshot=screenshot,
                grayscale=grayscale,
            )
            if result is not None:
                if offset:
                    return result.with_offset(offset)
                return result
        return None

    def press_back_button(self) -> None:
        """Presses the back button."""
        self.device.press_back_button()

    def swipe_down(
        self,
        x: int | None = None,
        sy: int | None = None,
        ey: int | None = None,
        duration: float = 1.0,
    ) -> None:
        """Perform a vertical swipe from top to bottom.

        Args:
            x (int, optional): X-coordinate of the swipe.
                Defaults to the horizontal center of the display.
            sy (int, optional): Start Y-coordinate. Defaults to the top edge (0).
            ey (int, optional): End Y-coordinate.
                Defaults to the bottom edge of the display.
            duration (float, optional): Duration of the swipe in seconds.
                Defaults to 1.0.
        """
        self._swipe_direction(
            _SwipeParams(_SwipeDirection.DOWN, x=x, start=sy, end=ey, duration=duration)
        )

    def swipe_up(
        self,
        x: int | None = None,
        sy: int | None = None,
        ey: int | None = None,
        duration: float = 1.0,
    ) -> None:
        """Perform a vertical swipe from bottom to top.

        Args:
            x (int, optional): X-coordinate of the swipe.
                Defaults to the horizontal center of the display.
            sy (int, optional): Start Y-coordinate.
                Defaults to the bottom edge of the display.
            ey (int, optional): End Y-coordinate. Defaults to the top edge (0).
            duration (float, optional): Duration of the swipe in seconds.
                Defaults to 1.0.
        """
        self._swipe_direction(
            _SwipeParams(_SwipeDirection.UP, x=x, start=sy, end=ey, duration=duration)
        )

    def swipe_right(
        self,
        y: int | None = None,
        sx: int | None = None,
        ex: int | None = None,
        duration: float = 1.0,
    ) -> None:
        """Perform a horizontal swipe from left to right.

        Args:
            y (int, optional): Y-coordinate of the swipe.
                Defaults to the vertical center of the display.
            sx (int, optional): Start X-coordinate.
                Defaults to the left edge (0).
            ex (int, optional): End X-coordinate.
                Defaults to the right edge of the display.
            duration (float, optional): Duration of the swipe in seconds.
                Defaults to 1.0.
        """
        self._swipe_direction(
            _SwipeParams(
                _SwipeDirection.RIGHT, y=y, start=sx, end=ex, duration=duration
            )
        )

    def swipe_left(
        self,
        y: int | None = None,
        sx: int | None = None,
        ex: int | None = None,
        duration: float = 1.0,
    ) -> None:
        """Perform a horizontal swipe from right to left.

        Args:
            y (int, optional): Y-coordinate of the swipe.
                Defaults to the vertical center of the display.
            sx (int, optional): Start X-coordinate.
                Defaults to the right edge of the display.
            ex (int, optional): End X-coordinate. Defaults to the left edge (0).
            duration (float, optional): Duration of the swipe in seconds.
                Defaults to 1.0.
        """
        self._swipe_direction(
            _SwipeParams(_SwipeDirection.LEFT, y=y, start=sx, end=ex, duration=duration)
        )

    def _swipe_direction(self, params: _SwipeParams) -> None:
        rx, ry = self.display_info.dimensions
        direction = params.direction

        coord = params.x if direction.is_vertical else params.y
        coord = (
            (rx // 2 if direction.is_vertical else ry // 2) if coord is None else coord
        )

        start = params.start or (
            0 if direction.is_increasing else (ry if direction.is_vertical else rx)
        )
        end = params.end or (
            (ry if direction.is_vertical else rx) if direction.is_increasing else 0
        )

        if (direction.is_increasing and start >= end) or (
            not direction.is_increasing and start <= end
        ):
            raise ValueError(
                f"Start must be {'less' if direction.is_increasing else 'greater'} "
                f"than end to swipe {direction.value}."
            )

        sx, sy, ex, ey = (
            (coord, start, coord, end)
            if direction.is_vertical
            else (start, coord, end, coord)
        )

        logging.debug(f"swipe_{direction} - from ({sx}, {sy}) to ({ex}, {ey})")
        self.device.swipe(
            Point(sx, sy).scale(self._scale_factor),
            Point(ex, ey).scale(self._scale_factor),
            duration=params.duration,
        )

    def hold(
        self,
        coordinates: Coordinates,
        duration: float = 3.0,
        blocking: bool = True,
        log: bool = True,
    ) -> threading.Thread | None:
        """Holds a point on the screen.

        Args:
            coordinates (Point): Point on the screen.
            duration (float, optional): Hold duration. Defaults to 3.0.
            blocking (bool, optional): Whether the call should happen async.
            log (bool, optional): Log the hold command.
        """
        point = Point(coordinates.x, coordinates.y).scale(self._scale_factor)

        if log:
            logging.debug(
                f"hold: ({coordinates.x}, {coordinates.y}) for {duration} seconds"
            )

        if blocking:
            self.device.hold(
                coordinates=point,
                duration=duration,
            )
            return None
        thread = threading.Thread(
            target=self.device.hold,
            kwargs={
                "coordinates": point,
                "duration": duration,
            },
            daemon=True,
        )
        thread.start()
        return thread

    T = TypeVar("T")

    @staticmethod
    def _execute_or_timeout(
        operation: Callable[[], T | None],
        timeout_message: str,
        delay: float = 0.5,
        timeout: float = 30,
        result_should_be_none: bool = False,
    ) -> T:
        """Repeatedly executes an operation until a desired result is reached.

        Raises:
            GameTimeoutError: Operation did not return the desired result.
        """
        time_spent_waiting: float = 0
        end_time: float = time() + timeout
        end_time_exceeded = False

        while True:
            result = operation()
            if result_should_be_none and result is None:
                return None  # type: ignore
            if not result_should_be_none and result is not None:
                return result

            sleep(delay)
            time_spent_waiting += delay

            if time_spent_waiting >= timeout or end_time_exceeded:
                raise GameTimeoutError(f"{timeout_message}")

            if end_time <= time():
                end_time_exceeded = True

    def _debug_save_screenshot(
        self, screenshot: np.ndarray, is_bgr: bool = False
    ) -> None:
        if self.disable_debug_screenshots:
            return
        debug_screenshot_save_num = (
            ConfigLoader.general_settings().logging.debug_save_screenshots
        )

        if debug_screenshot_save_num <= 0 or screenshot is None:
            return

        file_index = self._debug_screenshot_counter % debug_screenshot_save_num
        os.makedirs("debug", exist_ok=True)

        file_name = f"debug/{file_index}.png"
        try:
            os.makedirs(os.path.dirname(file_name), exist_ok=True)
            if is_bgr:
                image = Image.fromarray(Color.to_rgb(screenshot))
            else:
                image = Image.fromarray(screenshot)
            image.save(file_name)
            if file_index == 0:
                logging.debug(f"Saved screenshot {file_name}")
        except Exception as e:
            logging.warning(f"Cannot save debug screenshot: {file_name} Error: {e}")
            self.disable_debug_screenshots = True

        self._debug_screenshot_counter = file_index + 1
        return

    def _get_game_module(self) -> str:
        parts = self.__class__.__module__.split(".")
        try:
            index = parts.index("games")
            return parts[index + 1]
        except ValueError:
            raise ValueError("'games' not found in module path")
        except IndexError:
            raise ValueError("No module found after 'games' in module path")

    def _get_config_file_path(self) -> Path:
        if self._config_file_path is None:
            module = self._get_game_module()

            self._config_file_path = (
                ConfigLoader.games_dir()
                / module
                / (StringHelper.snake_to_pascal(module) + ".toml")
            )
            logging.debug(f"{module} config path: {self._config_file_path}")

        return self._config_file_path

    def get_template_dir_path(self) -> Path:
        """Retrieve path to images."""
        if self._template_dir_path is None:
            module = self._get_game_module()

            self._template_dir_path = ConfigLoader.games_dir() / module / "templates"
            logging.debug(f"{module} template path: {self._template_dir_path}")

        return self._template_dir_path

    def _get_custom_routine_config(self, name: str) -> MyCustomRoutineConfig:
        if hasattr(self.get_config(), name):
            attribute = getattr(self.get_config(), name)
            if isinstance(attribute, MyCustomRoutineConfig):
                return attribute
            else:
                raise ValueError(
                    f"Attribute '{name}' exists but is not a TaskListConfig"
                )
        raise AttributeError(f"Configuration has no attribute '{name}'")

    def _execute_custom_routine(self, config: MyCustomRoutineConfig) -> None:
        self._execute_tasks(config.tasks)
        while config.repeat:
            self._execute_tasks(config.tasks)

    def _get_game_commands(self) -> dict[str, CustomRoutineEntry] | None:
        commands = CUSTOM_ROUTINE_REGISTRY

        game_commands: dict[str, CustomRoutineEntry] | None = None
        for module, cmds in commands.items():
            if module in self.__module__:
                game_commands = cmds
                break
        return game_commands

    def _get_custom_routine_for_task(
        self, task: str, game_commands: dict[str, CustomRoutineEntry]
    ) -> CustomRoutineEntry | None:
        custom_routine: CustomRoutineEntry | None = None
        for label, custom_routine_entry in game_commands.items():
            if task == label:
                custom_routine = custom_routine_entry
                break
        return custom_routine

    def _execute_tasks(self, tasks: list[str]) -> None:
        game_commands = self._get_game_commands()
        if not game_commands:
            logging.error("Failed to load Custom Routine.")
            return

        for task in tasks:
            custom_routine = self._get_custom_routine_for_task(task, game_commands)
            if not custom_routine:
                logging.error(f"Task '{task}' not found")
                continue
            error = Execute.function(
                callable_function=custom_routine.func,
                kwargs=custom_routine.kwargs,
            )
            self._handle_task_error(task, error)
        return

    def _handle_task_error(self, task: str, error: Exception | None) -> None:
        if not error:
            return

        if isinstance(error, KeyboardInterrupt):
            raise KeyboardInterrupt

        if isinstance(error, cv2.error):
            if self._stream:
                logging.error(
                    "CV2 error attempting to clear caches and stopping device "
                    f"streaming, original error message: {error}"
                )
                self._stream.stop()
            else:
                logging.error(
                    "CV2 error attempting to clear caches, original error message: "
                    f"{error}"
                )
            IO.clear_cache()
            return
        if isinstance(error, AutoPlayerUnrecoverableError):
            logging.error(
                f"Task '{task}' failed with critical error: {error}, exiting..."
            )
            sys.exit(1)

        if isinstance(error, GameNotRunningOrFrozenError):
            logging.warning(
                f"Task '{task}' failed because the game crashed or is frozen, "
                "attempting to restart it."
            )
            self.force_stop_game()
            self.start_game()
            return

        if isinstance(error, AutoPlayerError):
            if not self.is_game_running():
                logging.warning(
                    f"Task '{task}' failed because the game crashed, "
                    "attempting to restart it."
                )
                self.start_game()
                return
            else:
                logging.warning(f"Task '{task}' failed moving to next Task.")
                return

        logging.error(
            f"Task '{task}' failed with unexpected Error: {error} moving to next Task."
        )
        return

    def _tap_till_template_disappears(
        self,
        template: str | Path,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        tap_delay: float = 10.0,
        sleep_duration: float = 0.5,
        error_message: str | None = None,
    ) -> None:
        max_tap_count = 3
        tap_count = 0
        time_since_last_tap = tap_delay  # force immediate first tap

        while result := self.game_find_template_match(
            template,
            threshold=threshold,
            grayscale=grayscale,
            crop_regions=crop_regions,
        ):
            if tap_count >= max_tap_count:
                message = error_message
                if not message:
                    message = f"Failed to tap: {template}, Template still visible."
                raise GameActionFailedError(message)
            if time_since_last_tap >= tap_delay:
                self.tap(result)
                tap_count += 1
                time_since_last_tap -= (
                    tap_delay  # preserve overflow - more accurate timing
                )

            sleep(sleep_duration)
            time_since_last_tap += sleep_duration

    def _tap_coordinates_till_template_disappears(
        self,
        coordinates: Coordinates,
        template: str | Path,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions | None = None,
        scale: bool = False,
        delay: float = 10.0,
    ) -> None:
        max_tap_count = 3
        tap_count = 0
        time_since_last_tap = delay  # force immediate first tap
        while self.game_find_template_match(
            template=template,
            threshold=threshold,
            grayscale=grayscale,
            crop_regions=(crop_regions if crop_regions else CropRegions()),
        ):
            if tap_count >= max_tap_count:
                # converting to point here for the error message.
                message = (
                    f"Failed to tap: {Point(coordinates.x, coordinates.y)}, "
                    f"Template: {template} still visible."
                )
                raise GameActionFailedError(message)
            if time_since_last_tap >= delay:
                self.tap(coordinates, scale=scale)
                tap_count += 1
                time_since_last_tap -= delay  # preserve overflow - more accurate timing

            sleep(0.5)
            time_since_last_tap += 0.5

    def assert_no_scaling(self, message: str | None) -> None:
        """Assert no scaling is required.

        This is meant for bots where exact pixel offsets are used or scaling breaks
        logic.

        Raises:
            AutoPlayerUnrecoverableError: if scaling is required.
        """
        if self.scale_factor != 1.0:
            raise AutoPlayerUnrecoverableError(
                message
                if message
                else f"Bot will only work with: {self.supported_resolutions[0]}"
            )

    def assert_frame_and_input_delay_below_threshold(
        self,
        max_frame_delay: int = 10,
        max_input_delay: int = 80,
    ) -> None:
        """Assert no frame and input lag is below threshold.

        This is meant for bots where fast input/reaction time is needed.

        Args:
            max_frame_delay(int, optional): maximum frame delay in milliseconds.
            max_input_delay(int, optional): maximum input delay in milliseconds.

        Raises:
            AutoPlayerUnrecoverableError: frame or input delay above max allowed value.
        """
        # Debug screenshots add additional IO, we can disable this here because we know
        # the feature needs to be fast if this function is called...
        self.disable_debug_screenshots = True

        start_time = time()
        _ = self.get_screenshot()
        total_time = (time() - start_time) * 1000
        if total_time > max_frame_delay:
            raise AutoPlayerUnrecoverableError(
                f"Screenshot/Frame delay: {int(total_time)} ms above max frame delay: "
                f"{max_frame_delay} ms exiting..."
            )
        logging.info(f"Screenshot/Frame delay: {int(total_time)} ms")

        total_time = 0.0
        iterations = 10
        for _ in range(iterations):
            start_time = time()
            self.tap(PointOutsideDisplay(), log=False)
            total_time += (time() - start_time) * 1000
        average_time = total_time / iterations
        if average_time > max_input_delay:
            raise AutoPlayerUnrecoverableError(
                f"Average input delay: {int(average_time)} ms above max input delay: "
                f"{max_input_delay} ms exiting..."
            )
        logging.info(f"Average input delay: {int(average_time)} ms")
