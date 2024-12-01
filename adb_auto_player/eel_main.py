import os
import sys
from typing import NoReturn

import eel
from eel.types import WebSocketT

import adb_auto_player.eel_functions as eel_functions

import adb_auto_player.update_manager as update_manager
import adb_auto_player.plugin_loader as plugin_loader
from adb_auto_player.logging_setup import (
    update_logging_from_config,
    setup_logging,
    enable_frontend_logs,
)

setup_logging()


def close(page: str, sockets: list[WebSocketT]) -> NoReturn:
    sys.exit(0)


def init() -> None:
    if getattr(sys, "frozen", False):
        path = os.path.join(sys._MEIPASS, "frontend", "build")  # type: ignore
        eel.init(path, [".svelte", ".html", ".js"])
    else:
        eel.init("frontend/src", [".svelte"])


def start() -> None:
    if getattr(sys, "frozen", False):
        eel.start("", port=8888, host="localhost", mode="chrome", close_callback=close)
    else:
        eel.start(
            {"port": 5173},  # type: ignore
            port=8888,
            host="localhost",
            mode="chrome",
            close_callback=close,
        )


def __start_eel() -> None:
    eel_functions.init()
    init()
    start()


if __name__ == "__main__":
    main_config = plugin_loader.get_main_config()
    update_logging_from_config(main_config)
    enable_frontend_logs()
    update_manager.version_updater()
    __start_eel()
