import sys

import eel
import adb_auto_player.eel_functions as eel_functions

import adb_auto_player.update_manager as update_manager
import adb_auto_player.plugin_loader as plugin_loader
from adb_auto_player.logging_setup import update_logging_from_config, setup_logging

setup_logging()


def __init_dev() -> None:
    eel.init("frontend/src", [".tsx", ".ts", ".jsx", ".js", ".html", ".svelte"])
    eel.start(
        {"port": 5173}, port=8888, host="localhost", mode="chrome"  # type: ignore
    )
    return None


def __init() -> None:
    eel.init("frontend/build", [".tsx", ".ts", ".jsx", ".js", ".html", ".svelte"])
    eel.start("", port=8888, mode="chrome")
    return None


def __start_eel() -> None:
    eel_functions.init()
    if getattr(sys, "frozen", False):
        __init()
    else:
        __init_dev()


if __name__ == "__main__":
    main_config = plugin_loader.get_main_config()
    update_logging_from_config(main_config)
    update_manager.version_updater()
    __start_eel()
