import logging
from typing import Dict, Any

from adbutils._device import AdbDevice
import adb_auto_player.adb as adb


class Plugin:
    def __init__(self, device: AdbDevice, config: Dict[str, Any]) -> None:
        self.device = device
        self.config = config

    def check_requirements(self) -> None:
        resolution = adb.get_screen_resolution(self.device)
        supported_resolution = self.config.get("plugin", {}).get(
            "supported_resolution", "1080x1920"
        )
        if resolution != supported_resolution:
            logging.critical(f"This plugin only supports {supported_resolution}")
