import adb_auto_player.logger as logging

from adbutils._device import AdbDevice
from typing import Dict, Any, NoReturn


def execute(device: AdbDevice, config: Dict[str, Any]) -> NoReturn:
    logging.critical_and_exit("WIP")
