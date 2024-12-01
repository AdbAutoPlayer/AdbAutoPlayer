from typing import Any, NoReturn

from adbutils._device import AdbDevice

import adb_auto_player.logger as logging


def execute(device: AdbDevice, config: dict[str, Any]) -> NoReturn:
    logging.critical_and_exit("WIP")
