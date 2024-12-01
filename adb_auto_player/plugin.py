from time import sleep

import adb_auto_player.logger as logging
import os.path
from abc import abstractmethod
from typing import Dict, Any, NoReturn

from adbutils._device import AdbDevice

import adb_auto_player.adb as adb
import adb_auto_player.screen_utils as screen_utils


class Plugin:
    def __init__(self, device: AdbDevice, config: Dict[str, Any]) -> None:
        self.device = device
        self.config = config
        self.store: Dict[str, Any] = {}

    @abstractmethod
    def get_template_dir_path(self) -> str:
        return ""

    def check_requirements(self) -> None | NoReturn:
        resolution = adb.get_screen_resolution(self.device)
        supported_resolution = self.config.get("plugin", {}).get(
            "supported_resolution", "1080x1920"
        )
        if resolution != supported_resolution:
            logging.critical_and_exit(
                f"This plugin only supports {supported_resolution}"
            )
        return None

    def find_first_template_center(
        self, template: str, grayscale: bool = False
    ) -> tuple[int, int] | None:
        template_path = os.path.join(
            self.get_template_dir_path(),
            template,
        )

        return screen_utils.find_center(
            self.device,
            template_path,
            grayscale=grayscale,
        )

    def find_all_template_centers(
        self, template: str, grayscale: bool = False
    ) -> list[tuple[int, int]] | None:
        template_path = os.path.join(
            self.get_template_dir_path(),
            template,
        )

        return screen_utils.find_all_centers(
            self.device,
            template_path,
            grayscale=grayscale,
        )

    def wait_for_template(
        self,
        template: str,
        grayscale: bool = False,
        delay: int = 1,
        timeout: int = 30,
        exit_message: str | None = None,
    ) -> tuple[int, int] | NoReturn:
        elapsed_time = 0
        while True:
            result = self.find_first_template_center(
                template,
                grayscale=grayscale,
            )
            if result is not None:
                logging.debug(f"{template} found")
                return result

            sleep(delay)
            elapsed_time += delay
            if elapsed_time >= timeout:
                if exit_message:
                    logging.critical_and_exit(f"{exit_message}")
                else:
                    logging.critical_and_exit(
                        f"Could not find Template: '{template}' after {timeout} seconds"
                    )

    def wait_until_template_disappears(
        self, template: str, delay: int = 1, timeout: int = 30
    ) -> None | NoReturn:
        elapsed_time = 0
        while True:
            if self.find_first_template_center(template) is None:
                logging.debug(f"{template} no longer visible")
                return None

            sleep(delay)
            elapsed_time += delay
            if elapsed_time >= timeout:
                logging.critical_and_exit(
                    f"Template: {template} is still visible after {timeout} seconds"
                )

    def wait_for_any_template(
        self, templates: list[str], delay: int = 3, timeout: int = 30
    ) -> tuple[str, int, int] | NoReturn:
        elapsed_time = 0
        while True:
            result = self.find_any_template_center(templates)

            if result is not None:
                return result

            sleep(delay)
            elapsed_time += delay
            if elapsed_time >= timeout:
                logging.critical_and_exit(
                    f"None of the templates {templates}"
                    f" were found after {timeout} seconds"
                )

    def find_any_template_center(
        self, templates: list[str]
    ) -> tuple[str, int, int] | None:
        for template in templates:
            result = self.find_first_template_center(template)
            if result is not None:
                x, y = result
                return template, x, y
        return None

    def press_back_button(self) -> None:
        self.device.keyevent(4)
