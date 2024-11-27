import logging

from ppadb.device import Device
from typing import Dict

from adb_auto_player.adb import get_screen_resolution


def execute(device: Device, config: Dict[str, str]) -> None:
    resolution = get_screen_resolution(device)

    if resolution != "1080x1920":
        logging.critical("This plugin only supports 1080x1920 Portrait Mode")

    logging.critical("WIP")
