import inspect
import threading
from typing import Any

import eel
from adbutils._device import AdbDevice

import adb_auto_player.adb as adb
import adb_auto_player.logger as logging
import adb_auto_player.plugin_loader as plugin_loader
from adb_auto_player.plugin import Plugin

main_config = plugin_loader.get_main_config()
plugins = plugin_loader.load_plugin_configs()
device: AdbDevice | None = None
global_plugin: dict[str, Any] | None = None
menu_options: list[dict[str, Any]] | None = None


def init() -> None:
    """This is only so functions here can be exposed."""
    return None


def get_device() -> AdbDevice:
    global device
    if device is None:
        device = adb.get_device(main_config)
    return device


def get_plugin() -> dict[str, Any] | None:
    global global_plugin, menu_options

    app = adb.get_currently_running_app(get_device())
    if global_plugin is not None:
        if app != global_plugin.get("package"):
            global_plugin = None
            menu_options = None

    if global_plugin is None:
        if app is None:
            return None
        global_plugin = plugin_loader.get_plugin_for_app(
            plugins,
            app,
        )

    return global_plugin


def get_game_object() -> Plugin | None:
    plugin = get_plugin()
    if plugin is None:
        return None

    module = plugin_loader.load_plugin_module(str(plugin.get("dir")))
    classes = [cls for name, cls in inspect.getmembers(module, inspect.isclass)]
    class_name = classes[0]
    game = class_name(get_device(), main_config)
    if isinstance(game, Plugin):
        return game
    return None


@eel.expose
def get_running_supported_game() -> str | None:
    plugin = get_plugin()
    if plugin is None:
        return None
    return plugin.get("name")


@eel.expose
def get_menu() -> list[str] | None:
    global menu_options
    game = get_game_object()
    if game is None:
        return None
    menu_options = game.get_menu_options()
    return [option.get("label", "") for option in menu_options]


@eel.expose
def execute(i: int) -> None:
    global menu_options
    if global_plugin is None or menu_options is None:
        logging.warning("No plugin loaded")
        return None

    if i < 0 or i >= len(menu_options):
        logging.warning("Invalid Menu Item")
        return None

    option = menu_options[i]
    action = option.get("action")
    kwargs = option.get("kwargs")
    if callable(action) and isinstance(kwargs, dict):
        action_thread = threading.Thread(target=action, kwargs=kwargs)
        action_thread.start()
        action_thread.join()
    else:
        logging.warning("Something went wrong executing the task")

    return None
