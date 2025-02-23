import io
from abc import abstractmethod
from pathlib import Path
from time import sleep, time
from typing import Any, TypeVar, Callable, Literal

from PIL import Image
from adbutils._device import AdbDevice
from pydantic import BaseModel

import adb_auto_player.adb as adb
import logging
import adb_auto_player.template_matching as template_matching
from adb_auto_player.command import Command
from adb_auto_player.exceptions import (
    UnsupportedResolutionException,
    TimeoutException,
    AdbException,
    NotInitializedError,
    NoPreviousScreenshotException,
)
from adb_auto_player.ipc.game_gui import GameGUIOptions, MenuOption
from adb_auto_player.template_matching import MatchMode


class Game:
    def __init__(self) -> None:
        self.device: AdbDevice | None = None
        self.config: BaseModel | None = None
        self.store: dict[str, Any] = {}
        self.previous_screenshot: Image.Image | None = None
        self.resolution: tuple[int, int] | None = None
        self.scale_factor: float | None = None
        self.supports_portrait: bool = False
        self.supports_landscape: bool = False

    @abstractmethod
    def get_template_dir_path(self) -> Path:
        pass

    @abstractmethod
    def load_config(self):
        pass

    @abstractmethod
    def get_cli_menu_commands(self) -> list[Command]:
        pass

    @abstractmethod
    def get_gui_options(self) -> GameGUIOptions:
        pass

    @abstractmethod
    def get_supported_resolutions(self) -> list[str]:
        pass

    @abstractmethod
    def get_config(self) -> BaseModel:
        pass

    def _get_menu_options_from_cli_menu(self) -> list[MenuOption]:
        menu_options = []
        for i, command in enumerate(self.get_cli_menu_commands()):
            menu_options.append(
                MenuOption(label=command.gui_label, args=[command.name])
            )
        return menu_options

    def check_requirements(self) -> None:
        """Validates Device properties such as resolution and orientation.

        Raises:
             UnsupportedResolutionException: Device resolution is not supported.
        """
        resolution = adb.get_screen_resolution(self.get_device())
        supported_resolutions = self.get_supported_resolutions()

        try:
            width, height = map(int, resolution.split("x"))
        except ValueError:
            raise UnsupportedResolutionException(
                f"Invalid resolution format: {resolution}"
            )

        is_supported = False
        for supported_resolution in supported_resolutions:
            if "x" in supported_resolution:
                if resolution == supported_resolution:
                    is_supported = True
                    break
            elif ":" in supported_resolution:
                try:
                    aspect_width, aspect_height = map(
                        int, supported_resolution.split(":")
                    )
                    if width * aspect_height == height * aspect_width:
                        is_supported = True
                        break
                except ValueError:
                    raise UnsupportedResolutionException(
                        f"Invalid aspect ratio format: {supported_resolution}"
                    )

        if not is_supported:
            raise UnsupportedResolutionException(
                "This bot only supports these resolutions: "
                f"{', '.join(supported_resolutions)}"
            )

        self.resolution = width, height

        if (
            self.supports_portrait
            and not self.supports_landscape
            and not adb.is_portrait(self.device)
        ):
            raise UnsupportedResolutionException(
                "This bot only works in Portrait mode: "
                "https://yulesxoxo.github.io/AdbAutoPlayer/user-guide/"
                "troubleshoot.html#this-bot-only-works-in-portrait-mode"
            )

        if (
            self.supports_landscape
            and not self.supports_portrait
            and adb.is_portrait(self.device)
        ):
            raise UnsupportedResolutionException(
                "This bot only works in Landscape mode: "
                "https://yulesxoxo.github.io/AdbAutoPlayer/user-guide/"
                "troubleshoot.html#this-bot-only-works-in-portrait-mode"
            )

        return None

    def get_scale_factor(self) -> float:
        if self.scale_factor:
            return self.scale_factor
        reference_resolution = (1080, 1920)
        if self.get_resolution() == reference_resolution:
            self.scale_factor = 1.0
        else:
            self.scale_factor = self.get_resolution()[0] / reference_resolution[0]
        return self.scale_factor

    def get_resolution(self) -> tuple[int, int]:
        if self.resolution is None:
            raise NotInitializedError()
        return self.resolution

    def set_device(self) -> None:
        resolutions = self.get_supported_resolutions()
        suggested_resolution = next((res for res in resolutions if "x" in res), None)
        logging.debug(f"Suggested Resolution: {suggested_resolution}")
        self.device = adb.get_device(suggested_resolution)
        self.check_requirements()

    def get_device(self) -> AdbDevice:
        if self.device is None:
            raise NotInitializedError()
        return self.device

    def click(
        self,
        x: int,
        y: int,
        scale: bool = False,
    ) -> None:
        if not scale:
            self.get_device().click(x, y)
            return None
        x, y = self.__scale_coordinates(x, y)
        self.get_device().click(x, y)
        return None

    def get_screenshot(self) -> Image.Image:
        """Gets screenshot from device using screencap.

        Raises:
            AdbException: Screenshot cannot be recorded
        """
        screenshot_data = self.get_device().shell("screencap -p", encoding=None)
        if isinstance(screenshot_data, bytes):
            png_start_index = screenshot_data.find(b"\x89PNG\r\n\x1a\n")
            # Slice the screenshot data to remove the warning
            # and keep only the PNG image data
            if png_start_index != -1:
                screenshot_data = screenshot_data[png_start_index:]
            self.previous_screenshot = Image.open(io.BytesIO(screenshot_data))
            return self.previous_screenshot
        raise AdbException(
            f"Screenshots cannot be recorded from device: {self.get_device().serial}"
        )

    def get_previous_screenshot(self) -> Image.Image:
        if self.previous_screenshot is not None:
            return self.previous_screenshot
        logging.warning("No previous screenshot")
        return self.get_screenshot()

    def __get_screenshot(self, previous_screenshot: bool):
        if previous_screenshot:
            return self.get_previous_screenshot()
        else:
            return self.get_screenshot()

    def wait_for_roi_change(
        self,
        threshold: float = 0.9,
        grayscale: bool = False,
        crop_left: float = 0.0,
        crop_right: float = 0.0,
        crop_top: float = 0.0,
        crop_bottom: float = 0.0,
        delay: float = 1,
        timeout: float = 30,
        timeout_message: str | None = None,
    ) -> bool:
        """Waits for a region of interest (ROI) on the screen to change.

        This function monitors a specific region of the screen (defined by the crop values).
        If the crop values are all set to 0, it will monitor the entire screen for changes.
        A change is detected based on a similarity threshold between current and previous screen regions.

        Raises:
            NoPreviousScreenshotException: No previous screenshot
            TimeoutException: If no change is detected within the timeout period.
            ValueError: Invalid crop values.
        """
        # Not using get_previous_screenshot is intentional here.
        # If you execute an action (e.g. click a button) then call wait_for_roi_change
        # There is a chance that by the time get_previous_screenshot takes
        # a screenshot because none exists that the animations are completed
        # this means the roi will never change
        prev = self.previous_screenshot
        if prev is None:
            raise NoPreviousScreenshotException(
                "Region of interest cannot have changed if "
                "there is no previous screenshot."
            )

        cropped, _, _ = template_matching.crop_image(
            image=prev,
            left=crop_left,
            right=crop_right,
            top=crop_top,
            bottom=crop_bottom,
        )

        def roi_changed() -> Literal[True] | None:
            screenshot, _, _ = template_matching.crop_image(
                image=self.get_screenshot(),
                left=crop_left,
                right=crop_right,
                top=crop_top,
                bottom=crop_bottom,
            )

            result = not template_matching.similar_image(
                base_image=cropped,
                template_image=screenshot,
                threshold=threshold,
                grayscale=grayscale,
            )

            if result is True:
                return True
            return None

        if timeout_message is None:
            timeout_message = (
                f"Region of Interest has not changed after {timeout} seconds"
            )

        return self.__execute_or_timeout(
            roi_changed, delay=delay, timeout=timeout, timeout_message=timeout_message
        )

    def find_template_match(
        self,
        template: str | Path,
        match_mode: template_matching.MatchMode = template_matching.MatchMode.BEST,
        threshold: float = 0.9,
        grayscale: bool = False,
        crop_left: float = 0.0,
        crop_right: float = 0.0,
        crop_top: float = 0.0,
        crop_bottom: float = 0.0,
        use_previous_screenshot: bool = False,
    ) -> tuple[int, int] | None:
        template_path = self.get_template_dir_path() / template

        base_image, left_offset, top_offset = template_matching.crop_image(
            image=self.__get_screenshot(previous_screenshot=use_previous_screenshot),
            left=crop_left,
            right=crop_right,
            top=crop_top,
            bottom=crop_bottom,
        )

        result = template_matching.find_template_match(
            base_image=base_image,
            template_image=template_matching.load_image(
                image_path=template_path,
                image_scale_factor=self.get_scale_factor(),
            ),
            match_mode=match_mode,
            threshold=threshold,
            grayscale=grayscale,
        )

        if result is None:
            return None

        x, y = result
        return x + left_offset, y + top_offset

    def find_all_template_matches(
        self,
        template: str | Path,
        threshold: float = 0.9,
        grayscale: bool = False,
        crop_left: float = 0.0,
        crop_right: float = 0.0,
        crop_top: float = 0.0,
        crop_bottom: float = 0.0,
        min_distance: int = 10,
        use_previous_screenshot: bool = False,
    ) -> list[tuple[int, int]]:
        template_path = self.get_template_dir_path() / template

        base_image, left_offset, top_offset = template_matching.crop_image(
            image=self.__get_screenshot(previous_screenshot=use_previous_screenshot),
            left=crop_left,
            right=crop_right,
            top=crop_top,
            bottom=crop_bottom,
        )

        result = template_matching.find_all_template_matches(
            base_image=base_image,
            template_image=template_matching.load_image(
                image_path=template_path,
                image_scale_factor=self.get_scale_factor(),
            ),
            threshold=threshold,
            grayscale=grayscale,
            min_distance=min_distance,
        )

        adjusted_result = [(x + left_offset, y + top_offset) for x, y in result]
        return adjusted_result

    def wait_for_template(
        self,
        template: str | Path,
        threshold: float = 0.9,
        grayscale: bool = False,
        crop_left: float = 0.0,
        crop_right: float = 0.0,
        crop_top: float = 0.0,
        crop_bottom: float = 0.0,
        delay: float = 1,
        timeout: float = 30,
        timeout_message: str | None = None,
    ) -> tuple[int, int]:
        """Waits for the template to appear in the screen.

        Raises:
            TimeoutException: Template not found.
        """

        def find_template() -> tuple[int, int] | None:
            result = self.find_template_match(
                template,
                threshold=threshold,
                grayscale=grayscale,
                crop_left=crop_left,
                crop_right=crop_right,
                crop_top=crop_top,
                crop_bottom=crop_bottom,
            )
            if result is not None:
                logging.debug(f"wait_for_template: {template} found")
            return result

        if timeout_message is None:
            timeout_message = (
                f"Could not find Template: '{template}' after {timeout} seconds"
            )

        return self.__execute_or_timeout(
            find_template, delay=delay, timeout=timeout, timeout_message=timeout_message
        )

    def wait_until_template_disappears(
        self,
        template: str | Path,
        threshold: float = 0.9,
        grayscale: bool = False,
        crop_left: float = 0.0,
        crop_right: float = 0.0,
        crop_top: float = 0.0,
        crop_bottom: float = 0.0,
        delay: float = 1,
        timeout: float = 30,
        timeout_message: str | None = None,
    ) -> None:
        """Waits for the template to disappear from the screen.

        Raises:
            TimeoutException: Template still visible.
        """

        def find_best_template() -> tuple[int, int] | None:
            result = self.find_template_match(
                template,
                threshold=threshold,
                grayscale=grayscale,
                crop_left=crop_left,
                crop_right=crop_right,
                crop_top=crop_top,
                crop_bottom=crop_bottom,
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

        self.__execute_or_timeout(
            find_best_template,
            delay=delay,
            timeout=timeout,
            timeout_message=timeout_message,
            result_should_be_none=True,
        )
        return None

    def wait_for_any_template(
        self,
        templates: list[str],
        threshold: float = 0.9,
        grayscale: bool = False,
        crop_left: float = 0.0,
        crop_right: float = 0.0,
        crop_top: float = 0.0,
        crop_bottom: float = 0.0,
        delay: float = 1,
        timeout: float = 30,
        timeout_message: str | None = None,
    ) -> tuple[str, int, int]:
        """Waits for any template to appear on the screen.

        Raises:
            TimeoutException: No template visible.
        """

        def find_template() -> tuple[str, int, int] | None:
            return self.find_any_template(
                templates,
                threshold=threshold,
                grayscale=grayscale,
                crop_left=crop_left,
                crop_right=crop_right,
                crop_top=crop_top,
                crop_bottom=crop_bottom,
            )

        if timeout_message is None:
            timeout_message = (
                f"None of the templates {templates} were found after {timeout} seconds"
            )

        return self.__execute_or_timeout(
            find_template, delay=delay, timeout=timeout, timeout_message=timeout_message
        )

    def find_any_template(
        self,
        templates: list[str],
        match_mode: MatchMode = MatchMode.BEST,
        threshold: float = 0.9,
        grayscale: bool = False,
        crop_left: float = 0.0,
        crop_right: float = 0.0,
        crop_top: float = 0.0,
        crop_bottom: float = 0.0,
        use_previous_screenshot: bool = False,
    ) -> tuple[str, int, int] | None:
        if not use_previous_screenshot:
            self.get_screenshot()
        for template in templates:
            result = self.find_template_match(
                template,
                match_mode=match_mode,
                threshold=threshold,
                grayscale=grayscale,
                crop_left=crop_left,
                crop_right=crop_right,
                crop_top=crop_top,
                crop_bottom=crop_bottom,
                use_previous_screenshot=True,
            )
            if result is not None:
                x, y = result
                return template, x, y
        return None

    def press_back_button(self) -> None:
        self.get_device().keyevent(4)

    def swipe_down(self, sy: int = 1350, ey: int = 500, duration: float = 1.0) -> None:
        if sy <= ey:
            raise ValueError(
                "sy (start y) must be greater than ey (end y) to swipe down."
            )

        logging.debug(f"swipe_down: {sy} to {ey}")
        self.swipe(sx=540, sy=sy, ex=540, ey=ey, duration=duration)

    def swipe_up(self, sy: int = 500, ey: int = 1350, duration: float = 1.0) -> None:
        if ey >= sy:
            raise ValueError("s (start y) must be smaller than ey (end y) to swipe up.")

        logging.debug(f"swipe_up: {sy} to {ey}")
        self.swipe(sx=540, sy=sy, ex=540, ey=ey, duration=duration)

    def hold(self, x: int, y: int, duration: float = 3.0) -> None:
        logging.debug(f"hold: ({x}, {y}) for {duration} seconds")
        self.swipe(sx=x, sy=y, ex=x, ey=y, duration=duration)

    def swipe(self, sx: int, sy: int, ex: int, ey: int, duration: float = 1.0):
        sx, sy, ex, ey = self.__scale_coordinates(sx, sy, ex, ey)
        self.get_device().swipe(sx=sx, sy=sy, ex=ex, ey=ey, duration=duration)
        sleep(2)

    T = TypeVar("T")

    @staticmethod
    def __execute_or_timeout(
        operation: Callable[[], T | None],
        timeout_message: str,
        delay: float = 1,
        timeout: float = 30,
        result_should_be_none: bool = False,
    ) -> T:
        """Repeatedly executes an operation until a desired result is reached.

        Raises:
            TimeoutException: Operation did not return the desired result.
        """
        time_spent_waiting: float = 0
        end_time = time() + timeout
        end_time_exceeded = False

        while True:
            result = operation()
            if result_should_be_none and result is None:
                return None  # type: ignore
            elif result is not None:
                return result

            sleep(delay)
            time_spent_waiting += delay

            if time_spent_waiting >= timeout or end_time_exceeded:
                raise TimeoutException(f"{timeout_message}")

            if end_time <= time():
                end_time_exceeded = True

    def __scale_coordinates(self, *coordinates: int) -> tuple[int, ...]:
        """Scale a variable number of coordinates by the given scale factor."""
        scale_factor = self.get_scale_factor()
        if scale_factor != 1.0:
            coordinates = tuple(int(round(c * scale_factor)) for c in coordinates)

        return coordinates
