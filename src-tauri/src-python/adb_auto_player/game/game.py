"""ADB Auto Player Game Base Module."""

import logging
import sys
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum, auto
from functools import cached_property, lru_cache
from pathlib import Path
from time import monotonic, perf_counter, sleep
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
from adb_auto_player.file_loader import SettingsLoader
from adb_auto_player.image_manipulation import (
    IO,
    Color,
    Cropping,
)
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.device import DisplayInfo, Resolution
from adb_auto_player.models.geometry import Coordinates, Point, PointOutsideDisplay
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.models.pydantic import TaskListSettings
from adb_auto_player.models.registries import CustomRoutineEntry
from adb_auto_player.models.template_matching import MatchMode, TemplateMatchResult
from adb_auto_player.registries import CUSTOM_ROUTINE_REGISTRY, GAME_REGISTRY
from adb_auto_player.template_matching import TemplateMatcher
from adb_auto_player.util import Execute
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


class _UndesiredResultError(Exception):
    """Used for _execute_or_timeout."""

    pass


class Game(ABC):
    """Generic Game class."""

    def __init__(self) -> None:
        """Initialize a game."""
        self.default_threshold: ConfidenceValue = ConfidenceValue("90%")

        # e.g. AFK Journey
        #   Global: com.farlightgames.igame.gp
        #   Vietnam: com.farlightgames.igame.gp.vn
        #   Global will cover both cases because it checks for the prefix
        self.package_name_prefixes: list[str] = []
        # Assuming landscape for most games
        self.base_resolution: Resolution = Resolution.from_string("1920x1080")
        self._device: AdbController | None = None
        self._stream: DeviceStream | None = None
        self._target_package_name: str | None = None

    @property
    @abstractmethod
    def settings(self) -> BaseModel:
        """Required property to return the game settings."""
        ...

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

    @property
    def center(self) -> Point:
        """Return center Point of display."""
        return self.base_resolution.center

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

        logging.warning("Game is not running, trying to start the game.")
        self.start_game()
        if not self.is_game_running():
            raise GameNotRunningOrFrozenError("Game could not be started, exiting...")
        return

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
        return

    def _set_device_resolution(self):
        if not SettingsLoader.adb_settings().device.use_wm_resize:
            return

        if not self.base_resolution == self.display_info.normalized_resolution:
            self.device.set_display_size(str(self.base_resolution))
        return

    def _check_requirements(self) -> None:
        """Validates Device properties such as resolution and orientation.

        Raises:
             UnsupportedResolutionException: Device resolution is not supported.
        """
        current = self.display_info.normalized_resolution
        base = self.base_resolution

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
        scale: bool = False,  # TODO remove later
        blocking: bool = True,
        # Assuming 30 FPS, 1 Tap per Frame
        non_blocking_sleep_duration: float | None = 1 / 30,
        log_message: str | None = None,
        log: bool = True,
    ) -> None:
        """Tap the screen on the given point.

        Args:
            coordinates (Coordinates): Point to click on.
            scale (bool, optional): Deprecated it does nothing.
            blocking (bool, optional): Whether to block the process and
                wait for ADBServer to confirm the tap has happened.
            non_blocking_sleep_duration (float, optional): Sleep time in seconds for
                non-blocking taps, needed to not DoS the ADBServer.
            log_message (str | None, optional): Custom Log message, default msg if None
            log (bool, optional): Log the tap command.
        """
        if log:
            log_message = (log_message or "Tapped") + f": {coordinates}"
        else:
            log_message = None

        # Perform the tap
        if blocking:
            self._click(
                coordinates,
                log_message,
            )
        else:
            thread = threading.Thread(
                target=self._click,
                args=(
                    coordinates,
                    log_message,
                ),
                daemon=True,
            )
            thread.start()
            if non_blocking_sleep_duration is not None:
                sleep(non_blocking_sleep_duration)

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
                return Color.to_bgr(image)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                data = self.device.screenshot()
                if isinstance(data, bytes):
                    image = IO.get_bgr_np_array_from_png_bytes(data)
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
        if not self._target_package_name:
            return
        self.device.stop_game(self._target_package_name)

    def is_game_running(self) -> bool:
        """Check if Game is still running."""
        if app := self.device.get_running_app():
            if self._target_package_name:
                return app == self._target_package_name

            if any(pn in app for pn in self.package_name_prefixes):
                self._target_package_name = app
                return True

        return False

    def start_game(self) -> None:
        """Start the Game.

        Raises:
            GameStartError: Game cannot be started.
        """
        if not self._target_package_name:
            return
        self.device.start_game(self._target_package_name)

    def restart_game(self):
        """Restart the Game.

        Calls force_stop_game() and start_game().
        """
        self.force_stop_game()
        self.start_game()

    def wait_for_roi_change(
        self,
        start_image: np.ndarray,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        delay: float = 0.5,
        timeout: float = 30,
        timeout_message: str | None = None,
    ) -> Literal[True]:
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
            bool: True if the region of interest has changed.

        Raises:
            GameTimeoutError: If no change is detected within the timeout period.
            ValueError: Invalid crop values.
        """
        crop_result = Cropping.crop(image=start_image, crop_regions=crop_regions)

        def roi_changed() -> Literal[True]:
            inner_crop_result = Cropping.crop(
                image=self.get_screenshot(),
                crop_regions=crop_regions,
            )

            if TemplateMatcher.similar_image(
                base_image=crop_result.image,
                template_image=inner_crop_result.image,
                threshold=threshold or self.default_threshold,
                grayscale=grayscale,
            ):
                raise _UndesiredResultError()
            return True

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
            image_path=self.template_dir / template,
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

        def find_template() -> TemplateMatchResult:
            result = self.game_find_template_match(
                template,
                threshold=threshold or self.default_threshold,
                grayscale=grayscale,
                crop_regions=crop_regions,
            )
            if result is not None:
                logging.debug(f"wait_for_template: {template} found")
                return result
            raise _UndesiredResultError()

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
            GameTimeoutError: Template still visible.
        """

        def find_best_template() -> None:
            if self.game_find_template_match(
                template,
                threshold=threshold or self.default_threshold,
                grayscale=grayscale,
                crop_regions=crop_regions,
            ):
                raise _UndesiredResultError()

            logging.debug(
                f"wait_until_template_disappears: {template} no longer visible"
            )

        if timeout_message is None:
            timeout_message = (
                f"Template: {template} is still visible after {timeout} seconds"
            )

        self._execute_or_timeout(
            find_best_template,
            delay=delay,
            timeout=timeout,
            timeout_message=timeout_message,
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
            GameTimeoutError: No template visible.
        """

        def find_template() -> TemplateMatchResult:
            find_template_result = self.find_any_template(
                templates,
                threshold=threshold or self.default_threshold,
                grayscale=grayscale,
                crop_regions=crop_regions,
            )

            if find_template_result:
                return find_template_result

            raise _UndesiredResultError()

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
            Point(sx, sy),
            Point(ex, ey),
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
        point = Point(coordinates.x, coordinates.y)

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
        operation: Callable[[], T],
        timeout_message: str,
        delay: float = 0.5,
        timeout: float = 30,
    ) -> T:
        end_time = monotonic() + timeout

        while True:
            try:
                return operation()
            except _UndesiredResultError:
                if monotonic() >= end_time:
                    raise GameTimeoutError(timeout_message)
                sleep(delay)

    def _get_game_module(self) -> str:
        parts = self.__class__.__module__.split(".")
        try:
            index = parts.index("games")
            return parts[index + 1]
        except ValueError:
            raise ValueError("'games' not found in module path")
        except IndexError:
            raise ValueError("No module found after 'games' in module path")

    @property
    def settings_file_path(self) -> Path:
        """Path for settings file."""
        settings_file: str | None = None
        for module, game in GAME_REGISTRY.items():
            if module == self._get_game_module():
                settings_file = game.settings_file
                break

        if settings_file is None:
            raise AutoPlayerUnrecoverableError("Game does not have any Settings")
        return SettingsLoader.settings_dir() / settings_file

    @cached_property
    def template_dir(self) -> Path:
        """Retrieve path to images."""
        module = self._get_game_module()
        template_dir = SettingsLoader.games_dir() / module / "templates"
        logging.debug(f"{module} template path: {template_dir}")
        return template_dir

    def _get_custom_routine_settings(self, name: str) -> TaskListSettings:
        if hasattr(self.settings, name):
            attribute = getattr(self.settings, name)
            if isinstance(attribute, TaskListSettings):
                return attribute
            else:
                raise ValueError(
                    f"Attribute '{name}' exists but is not MyCustomRoutineSettings"
                )
        raise AttributeError(f"Settings has no attribute '{name}'")

    def _execute_custom_routine(self, settings: TaskListSettings) -> None:
        game_commands = self._get_game_commands()
        if not game_commands:
            logging.error("Failed to load Custom Routine Tasks.")
            return

        custom_routines: dict[str, CustomRoutineEntry] = {}
        for task in settings.tasks:
            routine = self._get_custom_routine_for_task(task, game_commands)
            if not routine:
                logging.error(f"Task '{task}' not found")
            else:
                custom_routines[task] = routine

        if not custom_routines:
            logging.error("No Tasks found")
            return

        self._execute_tasks(custom_routines)
        while settings.repeat:
            self._execute_tasks(custom_routines)

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

    def _execute_tasks(self, tasks: dict[str, CustomRoutineEntry]) -> None:
        all_tasks_failed = True

        for task, routine in tasks.items():
            error = Execute.function(
                callable_function=routine.func,
                kwargs=routine.kwargs,
            )
            self._handle_task_error(task, error)
            if not error:
                all_tasks_failed = False

        if all_tasks_failed:
            self.restart_game()

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
            IO.cache_clear()
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
            self.restart_game()
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
        scale: bool = False,  # TODO remove later
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
                self.tap(coordinates)
                tap_count += 1
                time_since_last_tap -= delay  # preserve overflow - more accurate timing

            sleep(0.5)
            time_since_last_tap += 0.5

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

        start_time = perf_counter()
        _ = self.get_screenshot()
        total_time = (perf_counter() - start_time) * 1000
        if total_time > max_frame_delay:
            raise AutoPlayerUnrecoverableError(
                f"Screenshot/Frame delay: {int(total_time)} ms above max frame delay: "
                f"{max_frame_delay} ms exiting..."
            )
        logging.info(f"Screenshot/Frame delay: {int(total_time)} ms")

        total_time = 0.0
        iterations = 10
        for _ in range(iterations):
            start_time = perf_counter()
            self.tap(PointOutsideDisplay(), log=False, non_blocking_sleep_duration=None)
            total_time += (perf_counter() - start_time) * 1000
        average_time = total_time / iterations
        if average_time > max_input_delay:
            raise AutoPlayerUnrecoverableError(
                f"Average input delay: {int(average_time)} ms above max input delay: "
                f"{max_input_delay} ms exiting..."
            )
        logging.info(f"Average input delay: {int(average_time)} ms")

    @lru_cache
    def get_templates_from_dir(self, subdir: str) -> list[str]:
        """Return a list of all files inside a given template subdirectory.

        returns relative paths (e.g. 'power_saving_mode/1.png').
        """
        template_dir = self.template_dir / subdir

        return [
            f"{subdir}/{path.name}" for path in template_dir.iterdir() if path.is_file()
        ]
