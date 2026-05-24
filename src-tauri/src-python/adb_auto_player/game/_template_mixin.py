"""Template-matching mixin — find, wait, and compare screen templates."""

import logging
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from time import monotonic, sleep
from typing import Literal, TypeVar

import numpy as np
from adb_auto_player.exceptions import GameActionFailedError, GameTimeoutError
from adb_auto_player.image_manipulation import IO, Color, Cropping
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Coordinates, Point
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.models.template_matching import MatchMode, TemplateMatchResult
from adb_auto_player.template_matching import TemplateMatcher

from ._base import _GameBase

T = TypeVar("T")


class _UndesiredResultError(Exception):
    """Raised inside polling loops to signal the desired result has not yet occurred."""


class _TemplateMixin(_GameBase):
    """Mixin providing template-matching and wait operations."""

    # ------------------------------------------------------------------
    # Core timeout loop
    # ------------------------------------------------------------------

    @staticmethod
    def _execute_or_timeout(
        operation: Callable[[], T],
        timeout_message: str,
        delay: float = 0.5,
        timeout: float = 30,
    ) -> T:
        """Poll *operation* until it succeeds or *timeout* elapses.

        Args:
            operation: Callable that returns a value on success or raises
                _UndesiredResultError to signal "not yet".
            timeout_message: Message for GameTimeoutError if timeout expires.
            delay: Seconds to wait between polls.
            timeout: Maximum seconds to wait.

        Returns:
            Whatever *operation* returns on success.

        Raises:
            GameTimeoutError: If the timeout expires before success.
        """
        end_time = monotonic() + timeout
        while True:
            try:
                return operation()
            except _UndesiredResultError:
                if monotonic() >= end_time:
                    raise GameTimeoutError(timeout_message)
                sleep(delay)

    # ------------------------------------------------------------------
    # Single-template operations
    # ------------------------------------------------------------------

    def game_find_template_match(
        self,
        template: str | Path,
        match_mode: MatchMode = MatchMode.BEST,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        screenshot: np.ndarray | None = None,
    ) -> TemplateMatchResult | None:
        """Find a single template on the screen.

        Args:
            template (str | Path): Path to the template image (relative to
                template_dir).
            match_mode (MatchMode, optional): Defaults to MatchMode.BEST.
            threshold (ConfidenceValue, optional): Similarity threshold.
            grayscale (bool, optional): Convert to grayscale. Defaults to False.
            crop_regions (CropRegions, optional): Region to search within.
            screenshot (np.ndarray, optional): Reuse an existing screenshot.

        Returns:
            TemplateMatchResult | None
        """
        crop_result = Cropping.crop(
            image=screenshot if screenshot is not None else self.get_screenshot(),
            crop_regions=crop_regions,
        )

        match = TemplateMatcher.find_template_match(
            base_image=crop_result.image,
            template_image=self._load_image(template=template, grayscale=grayscale),
            match_mode=match_mode,
            threshold=threshold or self.default_threshold,
            grayscale=grayscale,
        )

        if match is None:
            return None

        return match.with_offset(crop_result.offset).to_template_match_result(
            template=str(template)
        )

    def find_worst_match(
        self,
        template: str | Path,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
    ) -> TemplateMatchResult | None:
        """Find the region that differs most from the template.

        Args:
            template (str | Path): Path to template image.
            grayscale (bool, optional): Convert to grayscale. Defaults to False.
            crop_regions (CropRegions, optional): Region to search within.

        Returns:
            None | TemplateMatchResult
        """
        crop_result = Cropping.crop(
            image=self.get_screenshot(), crop_regions=crop_regions
        )

        result = TemplateMatcher.find_worst_template_match(
            base_image=crop_result.image,
            template_image=self._load_image(template=template, grayscale=grayscale),
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
        """Find all non-overlapping occurrences of a template.

        Args:
            template (str | Path): Path to template image.
            threshold (ConfidenceValue, optional): Similarity threshold.
            grayscale (bool, optional): Convert to grayscale. Defaults to False.
            crop_regions (CropRegions, optional): Region to search within.
            min_distance (int, optional): Minimum pixel distance between matches.

        Returns:
            list[TemplateMatchResult]
        """
        crop_result = Cropping.crop(
            image=self.get_screenshot(), crop_regions=crop_regions
        )

        result = TemplateMatcher.find_all_template_matches(
            base_image=crop_result.image,
            template_image=self._load_image(template=template, grayscale=grayscale),
            threshold=threshold or self.default_threshold,
            grayscale=grayscale,
            min_distance=min_distance,
        )

        return [
            match.with_offset(crop_result.offset).to_template_match_result(
                template=str(template)
            )
            for match in result
        ]

    # ------------------------------------------------------------------
    # Multi-template operations
    # ------------------------------------------------------------------

    def find_any_template(
        self,
        templates: list[str],
        match_mode: MatchMode = MatchMode.BEST,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        screenshot: np.ndarray | None = None,
    ) -> TemplateMatchResult | None:
        """Return the first matching template found on the screen.

        Reuses a single screenshot for all template comparisons.

        Args:
            templates (list[str]): Templates to search for (checked in order).
            match_mode (MatchMode, optional): Defaults to MatchMode.BEST.
            threshold (ConfidenceValue, optional): Similarity threshold.
            grayscale (bool, optional): Convert to grayscale. Defaults to False.
            crop_regions (CropRegions, optional): Region to search within.
            screenshot (np.ndarray, optional): Reuse an existing screenshot.

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

    # ------------------------------------------------------------------
    # Wait operations
    # ------------------------------------------------------------------

    def wait_for_template(
        self,
        template: str | Path,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        delay: float = 0.5,
        timeout: float | None = None,
        timeout_message: str | None = None,
    ) -> TemplateMatchResult:
        """Wait until the template appears on screen.

        Args:
            template (str | Path): Template to search for.
            threshold (ConfidenceValue, optional): Similarity threshold.
            grayscale (bool, optional): Use grayscale matching.
            crop_regions (CropRegions, optional): Region to search within.
            delay (float, optional): Poll interval in seconds.
            timeout (float | None, optional): Timeout in seconds (uses global default).
            timeout_message (str | None, optional): Custom timeout message.

        Returns:
            TemplateMatchResult

        Raises:
            GameTimeoutError: Template not found within timeout.
        """
        if timeout is None:
            timeout = self.template_timeout

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
        timeout: float | None = None,
        timeout_message: str | None = None,
    ) -> None:
        """Wait until the template is no longer visible on screen.

        Args:
            template (str | Path): Template to monitor.
            threshold (ConfidenceValue, optional): Similarity threshold.
            grayscale (bool, optional): Use grayscale matching.
            crop_regions (CropRegions, optional): Region to search within.
            delay (float, optional): Poll interval in seconds.
            timeout (float | None, optional): Timeout in seconds.
            timeout_message (str | None, optional): Custom timeout message.

        Raises:
            GameTimeoutError: Template still visible after timeout.
        """
        if timeout is None:
            timeout = self.template_timeout

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
        timeout: float | None = None,
        timeout_message: str | None = None,
        ensure_order: bool = True,
    ) -> TemplateMatchResult:
        """Wait until any of the given templates appears on screen.

        Args:
            templates (list[str]): Templates to search for (checked in order).
            threshold (ConfidenceValue, optional): Similarity threshold.
            grayscale (bool, optional): Use grayscale matching.
            crop_regions (CropRegions, optional): Region to search within.
            delay (float, optional): Poll interval in seconds.
            timeout (float | None, optional): Timeout in seconds.
            timeout_message (str | None, optional): Custom timeout message.
            ensure_order (bool, optional): Re-check once to enforce template priority.

        Returns:
            TemplateMatchResult

        Raises:
            GameTimeoutError: No template found within timeout.
        """
        if timeout is None:
            timeout = self.template_timeout

        def find_template() -> TemplateMatchResult:
            result = self.find_any_template(
                templates,
                threshold=threshold or self.default_threshold,
                grayscale=grayscale,
                crop_regions=crop_regions,
            )
            if result:
                return result
            raise _UndesiredResultError()

        if timeout_message is None:
            timeout_message = (
                f"None of the templates {templates} were found after {timeout} seconds"
            )

        result = self._execute_or_timeout(
            find_template, delay=delay, timeout=timeout, timeout_message=timeout_message
        )

        if not ensure_order:
            return result

        # Re-check once to enforce template order (find_any_template reuses screenshot
        # within a single call so the re-check is cheap).
        sleep(delay)
        return self._execute_or_timeout(
            find_template, delay=0.5, timeout=3, timeout_message=timeout_message
        )

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
        """Wait for a region of interest on the screen to change.

        Args:
            start_image (np.ndarray): Reference image to compare against.
            threshold (ConfidenceValue, optional): Similarity threshold.
            grayscale (bool, optional): Use grayscale comparison.
            crop_regions (CropRegions, optional): Region to monitor.
            delay (float, optional): Poll interval in seconds.
            timeout (float, optional): Timeout in seconds.
            timeout_message (str | None, optional): Custom timeout message.

        Returns:
            True once a change is detected.

        Raises:
            GameTimeoutError: No change detected within timeout.
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

    # ------------------------------------------------------------------
    # Image loading helpers
    # ------------------------------------------------------------------

    def _load_image(
        self,
        template: str | Path,
        grayscale: bool = False,
    ) -> np.ndarray:
        return IO.load_image(
            image_path=self.template_dir / template,
            grayscale=grayscale,
        )

    # ------------------------------------------------------------------
    # Combined tap + template operations
    # ------------------------------------------------------------------

    def _tap_till_template_disappears(
        self,
        template: str,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        tap_delay: float = 10.0,
        sleep_duration: float = 0.5,
        error_message: str | None = None,
    ) -> None:
        """Tap the matched template location until it disappears.

        Args:
            template (str): Template to search and tap.
            threshold (ConfidenceValue, optional): Confidence threshold.
            grayscale (bool, optional): Use grayscale matching.
            crop_regions (CropRegions, optional): Region to search within.
            tap_delay (float, optional): Minimum seconds between taps.
            sleep_duration (float, optional): Poll interval in seconds.
            error_message (str | None, optional): Custom error on failure.
        """
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
                msg = (
                    error_message
                    or f"Failed to tap: {template}, Template still visible."
                )
                raise GameActionFailedError(msg)
            if time_since_last_tap >= tap_delay:
                self.tap(result)
                tap_count += 1
                time_since_last_tap -= tap_delay

            sleep(sleep_duration)
            time_since_last_tap += sleep_duration

    def _tap_coordinates_till_template_disappears(
        self,
        coordinates: Coordinates,
        template: str,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions | None = None,
        scale: bool = False,  # TODO remove later
        delay: float = 10.0,
        max_tap_count: int = 3,
    ) -> None:
        """Tap specific coordinates until a template disappears.

        Args:
            coordinates (Coordinates): Fixed point to tap.
            template (str): Template to monitor.
            threshold (ConfidenceValue, optional): Confidence threshold.
            grayscale (bool, optional): Use grayscale matching.
            crop_regions (CropRegions | None, optional): Region to search within.
            scale (bool, optional): Deprecated — does nothing.
            delay (float, optional): Minimum seconds between taps.
            max_tap_count (int, optional): Maximum taps before raising an error.
        """
        tap_count = 0
        time_since_last_tap = delay  # force immediate first tap
        while self.game_find_template_match(
            template=template,
            threshold=threshold,
            grayscale=grayscale,
            crop_regions=(crop_regions if crop_regions else CropRegions()),
        ):
            if tap_count >= max_tap_count:
                msg = (
                    f"Failed to tap: {Point(coordinates.x, coordinates.y)}, "
                    f"Template: {template} still visible."
                )
                raise GameActionFailedError(msg)
            if time_since_last_tap >= delay:
                self.tap(coordinates)
                tap_count += 1
                time_since_last_tap -= delay

            sleep(0.5)
            time_since_last_tap += 0.5

    @lru_cache
    def get_templates_from_dir(self, subdir: str) -> list[str]:
        """List all files inside a template subdirectory.

        Returns:
            Relative paths such as 'power_saving_mode/1.png'.
        """
        template_dir = self.template_dir / subdir
        return [
            f"{subdir}/{path.name}" for path in template_dir.iterdir() if path.is_file()
        ]
