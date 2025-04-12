"""ADB Auto Player Game Base Module."""

import logging
import os
import threading
from abc import abstractmethod
from collections.abc import Callable
from pathlib import Path
from time import sleep, time
from typing import Literal, NamedTuple, TypeVar

import cv2
import numpy as np
from adb_auto_player import (
    Command,
    ConfigLoader,
    DeviceStream,
    GameTimeoutError,
    GenericAdbError,
    NotInitializedError,
    StreamingNotSupportedError,
    UnsupportedResolutionError,
)
from adb_auto_player.adb import get_adb_device, get_screen_resolution, is_portrait
from adb_auto_player.ipc.game_gui import GameGUIOptions, MenuOption
from adb_auto_player.template_matching import (
    CropRegions,
    MatchMode,
    crop_image,
    find_all_template_matches,
    find_template_match,
    find_worst_template_match,
    load_image,
    similar_image,
)
from adbutils._device import AdbDevice
from deprecation import deprecated
from pydantic import BaseModel


class Coordinates(NamedTuple):
    """Coordinate named tuple."""

    x: int
    y: int


class Game:
    """Generic Game class."""

    def __init__(self) -> None:
        """Initialize a game."""
        self.config: BaseModel | None = None

        self.package_names: list[str] = []
        self.supports_landscape: bool = False
        self.supports_portrait: bool = False
        self.supported_resolutions: list[str] = ["1080x1920"]

        self._config_file_path: Path | None = None
        self._debug_screenshot_counter: int = 0
        self._device: AdbDevice | None = None
        self._previous_screenshot: np.ndarray | None = None
        self._resolution: tuple[int, int] | None = None
        self._scale_factor: float | None = None
        self._stream: DeviceStream | None = None
        self._template_dir_path: Path | None = None

    @abstractmethod
    def _load_config(self):
        """Required method to load the game configuration."""
        ...

    @abstractmethod
    def get_cli_menu_commands(self) -> list[Command]:
        """Required method to return the CLI menu commands."""
        ...

    @abstractmethod
    def get_gui_options(self) -> GameGUIOptions:
        """Required method to return the GUI options."""
        ...

    @abstractmethod
    def get_config(self) -> BaseModel:
        """Required method to return the game configuration."""
        ...

    def _get_menu_options_from_cli_menu(self) -> list[MenuOption]:
        """Get the menu options from the CLI menu commands."""
        menu_options = []
        for _, command in enumerate(self.get_cli_menu_commands()):
            menu_option = command.menu_option
            if menu_option is None:
                continue

            menu_options.append(menu_option)
        return menu_options

    def check_requirements(self) -> None:
        """Validates Device properties such as resolution and orientation.

        Raises:
             UnsupportedResolutionException: Device resolution is not supported.
        """
        resolution: str = get_screen_resolution(self.device)

        try:
            width, height = map(int, resolution.split("x"))
        except ValueError:
            raise UnsupportedResolutionError(f"Invalid resolution format: {resolution}")

        is_supported = False
        for supported_resolution in self.supported_resolutions:
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
                    raise UnsupportedResolutionError(
                        f"Invalid aspect ratio format: {supported_resolution}"
                    )

        if not is_supported:
            raise UnsupportedResolutionError(
                "This bot only supports these resolutions: "
                f"{', '.join(self.supported_resolutions)}"
            )

        self.resolution = width, height

        if (
            self.supports_portrait
            and not self.supports_landscape
            and not is_portrait(self.device)
        ):
            raise UnsupportedResolutionError(
                "This bot only works in Portrait mode: "
                "https://AdbAutoPlayer.github.io/AdbAutoPlayer/user-guide/"
                "troubleshoot.html#this-bot-only-works-in-portrait-mode"
            )

        if (
            self.supports_landscape
            and not self.supports_portrait
            and is_portrait(self.device)
        ):
            raise UnsupportedResolutionError(
                "This bot only works in Landscape mode: "
                "https://AdbAutoPlayer.github.io/AdbAutoPlayer/user-guide/"
                "troubleshoot.html#this-bot-only-works-in-portrait-mode"
            )

    def get_scale_factor(self) -> float:
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
        reference_resolution = (1080, 1920)
        if self.resolution == reference_resolution:
            self._scale_factor = 1.0
        else:
            self._scale_factor = self.resolution[0] / reference_resolution[0]
        logging.debug(f"scale_factor: {self._scale_factor}")
        return self._scale_factor

    @property
    def resolution(self) -> tuple[int, int]:
        """Get resolution."""
        if self._resolution is None:
            raise NotInitializedError()
        return self._resolution

    @resolution.setter
    def resolution(self, value: tuple[int, int]) -> None:
        """Set resolution."""
        self._resolution = value

    @property
    def device(self) -> AdbDevice:
        """Get device."""
        return self._device

    @device.setter
    def device(self, value: AdbDevice) -> None:
        """Set device."""
        self._device = value

    def open_eyes(self, device_streaming: bool = False) -> None:
        """Give the bot eyes.

        Set the device for the game and start the device stream.

        Args:
            device_streaming (bool, optional): Whether to start the device stream.
        """
        suggested_resolution: str | None = next(
            (res for res in self.supported_resolutions if "x" in res), None
        )
        logging.debug(f"Suggested Resolution: {suggested_resolution}")
        self.device = get_adb_device(suggested_resolution)
        self.check_requirements()

        config_streaming = (
            ConfigLoader().main_config.get("device", {}).get("streaming", True)
        )
        if not config_streaming:
            logging.warning("Device Streaming is disabled in Main Config")
            return
        if device_streaming:
            self.start_stream()

    def start_stream(self) -> None:
        """Start the device stream."""
        try:
            self._stream = DeviceStream(
                self.device,
            )
        except StreamingNotSupportedError as e:
            logging.warning(f"{e}")

        if self._stream is None:
            return

        self._stream.start()
        logging.info("Starting Device Stream...")
        time_waiting_for_stream_to_start = 0
        attempts = 10
        while True:
            if time_waiting_for_stream_to_start >= attempts:
                logging.error("Could not start Device Stream using screenshots instead")
                if self._stream:
                    self._stream.stop()
                    self._stream = None
                break
            if self._stream and self._stream.get_latest_frame():
                logging.info("Device Stream started")
                break
            sleep(1)
            time_waiting_for_stream_to_start += 1

    def tap(
        self,
        coordinates: Coordinates,
        scale: bool = False,
        blocking: bool = True,
        non_blocking_sleep_duration: float = 1 / 30,  # Assuming 30 FPS, 1 Tap per Frame
    ) -> None:
        """Tap the screen on the given coordinates.

        Args:
            coordinates (Coordinates): Coordinates to click on.
            scale (bool, optional): Whether to scale the coordinates.
            blocking (bool, optional): Whether to block the process and
                wait for ADBServer to confirm the tap has happened.
            non_blocking_sleep_duration (float, optional): Sleep time in seconds for
                non-blocking taps, needed to not DoS the ADBServer.
        """
        if scale:
            scaled_coords = Coordinates(*self._scale_coordinates(*coordinates))
            logging.debug(f"Scaled coordinates: {coordinates} => {scaled_coords}")
            coordinates = scaled_coords

        if blocking:
            self._click(coordinates)
        else:
            thread = threading.Thread(
                target=self._click, args=(coordinates,), daemon=True
            )
            thread.start()
            sleep(non_blocking_sleep_duration)

    @deprecated(details="Use 'tap' instead.")
    def click(
        self,
        coordinates: Coordinates,
        scale: bool = False,
    ) -> None:
        """Click on the given coordinates.

        Args:
            coordinates (Coordinates): Coordinates to click on.
            scale (bool, optional): Whether to scale the coordinates.
        """
        if scale:
            scaled_coords = Coordinates(*self._scale_coordinates(*coordinates))
            logging.debug(f"Scaled coordinates: {coordinates} => {scaled_coords}")
            coordinates = scaled_coords
        self._click(coordinates)

    def _click(self, coordinates: Coordinates) -> None:
        with self.device.shell(
            f"input tap {coordinates.x} {coordinates.y}",
            timeout=3,  # if the click didn't happen in 3 seconds it's never happening
            stream=True,
        ) as connection:
            logging.debug(f"Clicked Coordinates: {coordinates}")
            # without this it breaks for people with slower CPUs
            # need to think of a better solution
            connection.read_until_close()

    def get_screenshot(self) -> np.ndarray:
        """Gets screenshot from device using stream or screencap.

        Raises:
            AdbException: Screenshot cannot be recorded
        """
        if self._stream:
            image = self._stream.get_latest_frame()
            if image:
                self._previous_screenshot = image
                self._debug_save_screenshot()
                return image
            logging.error(
                "Could not retrieve latest Frame from Device Stream using screencap..."
            )
        # using shell with encoding directly does not close the file descriptor
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with self.device.shell("screencap -p", stream=True) as c:
                    screenshot_data = c.read_until_close(encoding=None)
                if isinstance(screenshot_data, bytes):
                    return self._get_numpy_array_from_bytes(screenshot_data)
            except (OSError, ValueError) as e:
                logging.debug(
                    f"Attempt {attempt + 1}/{max_retries}: "
                    f"Failed to process screenshot: {e}"
                )
                sleep(0.1)

        raise GenericAdbError(
            f"Screenshots cannot be recorded from device: {self.device.serial}"
        )

    def _get_numpy_array_from_bytes(self, screenshot_data: bytes) -> np.ndarray:
        """Converts bytes to numpy array.

        Raises:
            OSError
            ValueError
        """
        png_start_index = screenshot_data.find(b"\x89PNG\r\n\x1a\n")
        # Slice the screenshot data to remove the warning
        # and keep only the PNG image data
        if png_start_index != -1:
            screenshot_data = screenshot_data[png_start_index:]

        np_data = np.frombuffer(screenshot_data, dtype=np.uint8)
        img = cv2.imdecode(np_data, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode screenshot image data")
        self._previous_screenshot = img
        self._debug_save_screenshot()
        return self._previous_screenshot

    def get_previous_screenshot(self) -> np.ndarray:
        """Get the previous screenshot."""
        if self._previous_screenshot is not None:
            return self._previous_screenshot
        logging.warning("No previous screenshot")
        return self.get_screenshot()

    def _get_screenshot(self, previous_screenshot: bool) -> np.ndarray:
        """Get screenshot depending on stream or not."""
        if self._stream:
            return self.get_screenshot()
        if previous_screenshot:
            return self.get_previous_screenshot()
        else:
            return self.get_screenshot()

    def wait_for_roi_change(  # noqa: PLR0913 - TODO: Consolidate more.
        self,
        start_image: np.ndarray,
        threshold: float = 0.9,
        grayscale: bool = False,
        crop: CropRegions = CropRegions(),
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
            crop (Crop): Crop percentages for trimming the image. Defaults to Crop().
            delay (float): Delay between checks in seconds. Defaults to 0.5.
            timeout (float): Timeout in seconds. Defaults to 30.
            timeout_message (str | None): Custom timeout message. Defaults to None.

        Returns:
            bool: True if the region of interest has changed, False otherwise.

        Raises:
            NoPreviousScreenshotException: No previous screenshot
            TimeoutException: If no change is detected within the timeout period.
            ValueError: Invalid crop values.
        """
        cropped, _, _ = crop_image(image=start_image, crop=crop)

        def roi_changed() -> Literal[True] | None:
            screenshot, _, _ = crop_image(image=self.get_screenshot(), crop=crop)

            result = not similar_image(
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

        return self._execute_or_timeout(
            roi_changed, delay=delay, timeout=timeout, timeout_message=timeout_message
        )

    # TODO: Change this functio name.
    # It is the same as template_matching.find_template_match
    def game_find_template_match(  # noqa: PLR0913 - TODO: Consolidate more.
        self,
        template: str | Path,
        match_mode: MatchMode = MatchMode.BEST,
        threshold: float = 0.9,
        grayscale: bool = False,
        crop: CropRegions = CropRegions(),
        use_previous_screenshot: bool = False,
    ) -> tuple[int, int] | None:
        """Find a template on the screen.

        Args:
            template (str | Path): Path to the template image.
            match_mode (MatchMode, optional): Defaults to MatchMode.BEST.
            threshold (float, optional): Image similarity threshold. Defaults to 0.9.
            grayscale (bool, optional): Convert to grayscale boolean. Defaults to False.
            crop (Crop, optional): Crop percentages. Defaults to Crop().
            use_previous_screenshot (bool, optional): Defaults to False.

        Returns:
            tuple[int, int] | None: Coordinates of the match, or None if not found.
        """
        template_path = self.get_template_dir_path() / template

        base_image, left_offset, top_offset = crop_image(
            image=self._get_screenshot(previous_screenshot=use_previous_screenshot),
            crop=crop,
        )

        result = find_template_match(
            base_image=base_image,
            template_image=load_image(
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

    def find_worst_match(
        self,
        template: str | Path,
        grayscale: bool = False,
        crop: CropRegions = CropRegions(),
    ) -> None | tuple[int, int]:
        """Find the most different match.

        Args:
            template (str | Path): Path to template image.
            grayscale (bool, optional): Convert to grayscale boolean. Defaults to False.
            crop (CropRegions, optional): Crop percentages. Defaults to CropRegions().

        Returns:
            None | tuple[int, int]: Coordinates of worst match.
        """
        template_path: Path = self.get_template_dir_path() / template
        base_image, left_offset, top_offset = crop_image(
            image=self._get_screenshot(previous_screenshot=False), crop=crop
        )

        result = find_worst_template_match(
            base_image=base_image,
            template_image=load_image(
                image_path=template_path,
                image_scale_factor=self.get_scale_factor(),
            ),
            grayscale=grayscale,
        )

        if result is None:
            return None
        x, y = result
        return x + left_offset, y + top_offset

    def find_all_template_matches(  # noqa: PLR0913 - TODO: Consolidate more.
        self,
        template: str | Path,
        threshold: float = 0.9,
        grayscale: bool = False,
        crop: CropRegions = CropRegions(),
        min_distance: int = 10,
        use_previous_screenshot: bool = False,
    ) -> list[tuple[int, int]]:
        """Find all matches.

        Args:
            template (str | Path): Path to template image.
            threshold (float, optional): Image similarity threshold. Defaults to 0.9.
            grayscale (bool, optional): Convert to grayscale boolean. Defaults to False.
            crop (CropRegions, optional): Crop percentages. Defaults to CropRegions().
            min_distance (int, optional): Minimum distance between matches.
                Defaults to 10.
            use_previous_screenshot (bool, optional): Defaults to False.

        Returns:
            list[tuple[int, int]]: List of found coordinates.
        """
        template_path: Path = self.get_template_dir_path() / template

        base_image, left_offset, top_offset = crop_image(
            image=self._get_screenshot(previous_screenshot=use_previous_screenshot),
            crop=crop,
        )

        result: list[tuple[int, int]] = find_all_template_matches(
            base_image=base_image,
            template_image=load_image(
                image_path=template_path,
                image_scale_factor=self.get_scale_factor(),
            ),
            threshold=threshold,
            grayscale=grayscale,
            min_distance=min_distance,
        )

        adjusted_result: list[tuple[int, int]] = [
            (x + left_offset, y + top_offset) for x, y in result
        ]
        return adjusted_result

    def wait_for_template(  # noqa: PLR0913 - TODO: Consolidate more.
        self,
        template: str | Path,
        threshold: float = 0.9,
        grayscale: bool = False,
        crop: CropRegions = CropRegions(),
        delay: float = 0.5,
        timeout: float = 30,
        timeout_message: str | None = None,
    ) -> tuple[int, int]:
        """Waits for the template to appear in the screen.

        Raises:
            TimeoutError: Template not found.
        """

        def find_template() -> tuple[int, int] | None:
            result: tuple[int, int] | None = self.game_find_template_match(
                template,
                threshold=threshold,
                grayscale=grayscale,
                crop=crop,
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

    def wait_until_template_disappears(  # noqa: PLR0913 - TODO: Consolidate more.
        self,
        template: str | Path,
        threshold: float = 0.9,
        grayscale: bool = False,
        crop: CropRegions = CropRegions(),
        delay: float = 0.5,
        timeout: float = 30,
        timeout_message: str | None = None,
    ) -> None:
        """Waits for the template to disappear from the screen.

        Raises:
            TimeoutException: Template still visible.
        """

        def find_best_template() -> tuple[int, int] | None:
            result: tuple[int, int] | None = self.game_find_template_match(
                template,
                threshold=threshold,
                grayscale=grayscale,
                crop=crop,
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

    def wait_for_any_template(  # noqa: PLR0913 - TODO: Consolidate more.
        self,
        templates: list[str],
        threshold: float = 0.9,
        grayscale: bool = False,
        crop: CropRegions = CropRegions(),
        delay: float = 0.5,
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
                crop=crop,
            )

        if timeout_message is None:
            timeout_message = (
                f"None of the templates {templates} were found after {timeout} seconds"
            )

        return self._execute_or_timeout(
            find_template, delay=delay, timeout=timeout, timeout_message=timeout_message
        )

    def find_any_template(  # noqa: PLR0913 - TODO: Consolidate more.
        self,
        templates: list[str],
        match_mode: MatchMode = MatchMode.BEST,
        threshold: float = 0.9,
        grayscale: bool = False,
        crop: CropRegions = CropRegions(),
        use_previous_screenshot: bool = False,
    ) -> tuple[str, int, int] | None:
        """Find any first template on the screen.

        Args:
            templates (list[str]): List of templates to search for.
            match_mode (MatchMode, optional): String enum. Defaults to MatchMode.BEST.
            threshold (float, optional): Image similarity threshold. Defaults to 0.9.
            grayscale (bool, optional): Convert to grayscale boolean. Defaults to False.
            crop (CropRegions, optional): Crop percentages. Defaults to CropRegions().
            use_previous_screenshot (bool, optional): Defaults to False.

        Returns:
            tuple[str, int, int] | None: Coordinates of the match, or None if not found.
        """
        if not use_previous_screenshot:
            self.get_screenshot()
        for template in templates:
            result: tuple[int, int] | None = self.game_find_template_match(
                template,
                match_mode=match_mode,
                threshold=threshold,
                grayscale=grayscale,
                crop=crop,
                use_previous_screenshot=True,
            )
            if result is not None:
                x, y = result
                return template, x, y
        return None

    def press_back_button(self) -> None:
        """Presses the back button."""
        with self.device.shell("input keyevent 4", stream=True) as connection:
            logging.debug("pressed back button")
            connection.read_until_close()

    def swipe_down(self, sy: int = 1350, ey: int = 500, duration: float = 1.0) -> None:
        """Swipes the screen down.

        Args:
            sy (int, optional): Start Y coordinate. Defaults to 1350.
            ey (int, optional): End Y coordinate. Defaults to 500.
            duration (float, optional): Swipe duration. Defaults to 1.0.

        Raises:
            ValueError: If sy is greater than or equal to ey.
        """
        if sy <= ey:
            raise ValueError(
                "sy (start y) must be greater than ey (end y) to swipe down."
            )

        logging.debug(f"swipe_down: {sy} to {ey}")
        self.swipe(sx=540, sy=sy, ex=540, ey=ey, duration=duration)

    def swipe_up(self, sy: int = 500, ey: int = 1350, duration: float = 1.0) -> None:
        """Swipes the screen up.

        Args:
            sy (int, optional): Start Y coordinate. Defaults to 500.
            ey (int, optional): End Y coordinate. Defaults to 1350.
            duration (float, optional): Swipe duration. Defaults to 1.0.

        Raises:
            ValueError: If ey is less than or equal to sy.
        """
        if ey >= sy:
            raise ValueError("s (start y) must be smaller than ey (end y) to swipe up.")

        logging.debug(f"swipe_up: {sy} to {ey}")
        self.swipe(sx=540, sy=sy, ex=540, ey=ey, duration=duration)

    def hold(self, x: int, y: int, duration: float = 3.0) -> None:
        """Holds a point on the screen.

        Args:
            x (int): X coordinate.
            y (int): Y coordinate.
            duration (float, optional): Hold duration. Defaults to 3.0.
        """
        logging.debug(f"hold: ({x}, {y}) for {duration} seconds")
        self.swipe(sx=x, sy=y, ex=x, ey=y, duration=duration)

    def swipe(self, sx: int, sy: int, ex: int, ey: int, duration: float = 1.0) -> None:
        """Swipes the screen.

        Args:
            sx (int): Start X coordinate.
            sy (int): Start Y coordinate.
            ex (int): End X coordinate.
            ey (int): End Y coordinate.
            duration (float, optional): Swipe duration. Defaults to 1.0.
        """
        sx, sy, ex, ey = self._scale_coordinates(sx, sy, ex, ey)
        self.device.swipe(sx=sx, sy=sy, ex=ex, ey=ey, duration=duration)
        sleep(2)

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
            TimeoutError: Operation did not return the desired result.
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

    def _scale_coordinates(self, *coordinates: int) -> tuple[int, ...]:
        """Scale a variable number of coordinates by the given scale factor."""
        scale_factor: float = self.get_scale_factor()
        if scale_factor != 1.0:
            coordinates = tuple(round(c * scale_factor) for c in coordinates)

        return coordinates

    def _debug_save_screenshot(self) -> None:
        logging_config = ConfigLoader().main_config.get("logging", {})
        debug_screenshot_save_num = logging_config.get("debug_save_screenshots", 0)
        log_level = logging_config.get("level", "INFO")

        screenshot = self._previous_screenshot
        if debug_screenshot_save_num <= 0 or screenshot is None or log_level != "DEBUG":
            return

        file_index = self._debug_screenshot_counter % debug_screenshot_save_num
        os.makedirs("debug", exist_ok=True)

        file_name = f"debug/{file_index}.png"
        screenshot.save(file_name)
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
                ConfigLoader().games_dir / module / (snake_to_pascal(module) + ".toml")
            )
            logging.debug(f"{module} config path: {self._config_file_path}")

        return self._config_file_path

    def get_template_dir_path(self) -> Path:
        """Retrieve path to images."""
        if self._template_dir_path is None:
            module = self._get_game_module()

            self._template_dir_path = ConfigLoader().games_dir / module / "templates"
            logging.debug(f"{module} template path: {self._template_dir_path}")

        return self._template_dir_path


def snake_to_pascal(s: str):
    """snake_case to PascalCase."""
    return "".join(word.capitalize() for word in s.split("_"))
