import io
from abc import abstractmethod
from pathlib import Path
from time import sleep, time
from typing import Any, TypeVar, Callable

from PIL import Image
from adbutils._device import AdbDevice
from pydantic import BaseModel

import adb_auto_player.adb as adb
import logging
import adb_auto_player.screen_utils as screen_utils
from adb_auto_player.command import Command
from adb_auto_player.exceptions import UnsupportedResolutionException, TimeoutException, AdbException


class Game:
    def __init__(self) -> None:
        self.device: AdbDevice|None  = None
        self.config: BaseModel|None = None
        self.store: dict[str, Any] = {}
        self.previous_screenshot: Image.Image|None = None

    @abstractmethod
    def get_template_dir_path(self) -> Path:
        pass

    @abstractmethod
    def load_config(self):
        pass

    @abstractmethod
    def get_menu_commands(self) -> list[Command]:
        pass

    @abstractmethod
    def get_supported_resolutions(self) -> list[str]:
        pass

    def check_requirements(self) -> None:
        """
        :raises UnsupportedResolutionException:
        """
        resolution = adb.get_screen_resolution(self.device)
        supported_resolutions = self.get_supported_resolutions()
        if resolution not in supported_resolutions:
            raise UnsupportedResolutionException(
                f"This plugin only supports these resolutions: {", ".join(supported_resolutions)}"
            )
        return None

    def set_device(self) -> None:
        self.device = adb.get_device()

    def get_screenshot(self) -> Image.Image:
        """
        :raises AdbException: Screenshot cannot be recorded
        """
        screenshot_data = self.device.shell("screencap -p", encoding=None)
        if isinstance(screenshot_data, bytes):
            self.previous_screenshot = Image.open(io.BytesIO(screenshot_data))
            return self.previous_screenshot
        raise AdbException(f"Screenshots cannot be recorded from device: {self.device.serial}")

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

    def find_template_match(
        self,
        template: str,
        match_mode: screen_utils.MatchMode = screen_utils.MatchMode.BEST,
        threshold: float = 0.9,
        grayscale: bool = False,
        use_previous_screenshot: bool = False,
    ) -> tuple[int, int] | None:
        template_path = self.get_template_dir_path() / template

        return screen_utils.find_template_match(
            base_image=self.__get_screenshot(previous_screenshot=use_previous_screenshot),
            template_image=screen_utils.load_image(image_path=template_path),
            match_mode=match_mode,
            threshold=threshold,
            grayscale=grayscale,
        )

    def find_all_template_matches(
        self,
        template: str,
        threshold: float = 0.9,
        grayscale: bool = False,
        min_distance: int = 10,
        use_previous_screenshot: bool = False,
    ) -> list[tuple[int, int]]:
        template_path = self.get_template_dir_path() / template

        return screen_utils.find_all_template_matches(
            base_image=self.__get_screenshot(previous_screenshot=use_previous_screenshot),
            template_image=screen_utils.load_image(image_path=template_path),
            threshold=threshold,
            grayscale=grayscale,
            min_distance=min_distance,
        )

    def wait_for_template(
        self,
        template: str,
        threshold: float = 0.9,
        grayscale: bool = False,
        delay: float = 1,
        timeout: float = 30,
        timeout_message: str | None = None,
    ) -> tuple[int, int]:
        """
        :raises TimeoutException:
        """

        def find_template() -> tuple[int, int] | None:
            result = self.find_template_match(
                template,
                threshold=threshold,
                grayscale=grayscale,
            )
            if result is not None:
                logging.debug(f"{template} found")
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
        template: str,
        threshold: float = 0.9,
        grayscale: bool = False,
        delay: float = 1,
        timeout: float = 30,
        timeout_message: str | None = None,
    ) -> None:
        """
        :raises TimeoutException:
        """

        def find_best_template() -> tuple[int, int] | None:
            result = self.find_template_match(
                template,
                threshold=threshold,
                grayscale=grayscale,
            )
            if result is None:
                logging.debug(f"{template} no longer visible")

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
        )
        return None

    def wait_for_any_template(
        self,
        templates: list[str],
        threshold: float = 0.9,
        grayscale: bool = False,
        delay: float = 3,
        timeout: float = 30,
        timeout_message: str | None = None,
    ) -> tuple[str, int, int]:
        """
        :raises TimeoutException:
        """

        def find_template() -> tuple[str, int, int] | None:
            return self.find_any_template_center(
                templates,
                threshold=threshold,
                grayscale=grayscale,
            )

        if timeout_message is None:
            timeout_message = (
                f"None of the templates {templates} were found after {timeout} seconds"
            )

        return self.__execute_or_timeout(
            find_template, delay=delay, timeout=timeout, timeout_message=timeout_message
        )

    def find_any_template_center(
        self,
        templates: list[str],
        threshold: float = 0.9,
        grayscale: bool = False,
    ) -> tuple[str, int, int] | None:
        self.get_screenshot()
        for template in templates:
            result = self.find_template_match(
                template,
                threshold=threshold,
                grayscale=grayscale,
                use_previous_screenshot=True,
            )
            if result is not None:
                x, y = result
                return template, x, y
        return None

    def press_back_button(self) -> None:
        self.device.keyevent(4)

    T = TypeVar("T")

    def __execute_or_timeout(
        self,
        operation: Callable[[], T | None],
        timeout_message: str,
        delay: float = 1,
        timeout: float = 30,
        result_should_be_none: bool = False,
    ) -> T:
        """
        :raises TimeoutException:
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
