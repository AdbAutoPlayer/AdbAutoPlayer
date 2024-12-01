import inspect
import logging
import multiprocessing.queues
import sys
from logging.handlers import QueueHandler
from multiprocessing import Process
from typing import Any, NoReturn

import eel
from adbutils._device import AdbDevice

import adb_auto_player.adb as adb
import adb_auto_player.plugin_loader as plugin_loader
from adb_auto_player import logging_setup
from adb_auto_player.plugin import Plugin

main_config = plugin_loader.get_main_config()
plugins = plugin_loader.load_plugin_configs()
global_device: AdbDevice | None = None
global_plugin: dict[str, Any] | None = None
menu_options: list[dict[str, Any]] | None = None
action_process: Process | None = None


def init() -> None:
    """This is only so functions here can be exposed."""
    return None


def get_device() -> AdbDevice | None:
    global global_device
    if global_device is None:
        try:
            global_device = adb.get_device(main_config)
        except SystemExit:
            return None
    return global_device


def get_plugin() -> dict[str, Any] | None:
    global global_plugin, menu_options

    device = get_device()
    if device is None:
        return None

    try:
        app = adb.get_currently_running_app(device)
    except SystemExit:
        return None
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
    device = get_device()
    if device is None:
        return None
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
    global action_process
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

        action_process = Process(
            target=run_action_in_process,
            args=(
                action.__name__,
                kwargs,
                logging_setup.get_log_queue(),
                logging.getLogger().getEffectiveLevel(),
            ),
        )
        action_process.daemon = True
        action_process.start()
    else:
        logging.warning("Something went wrong executing the task")
    return None


def run_action_in_process(
    action: str,
    kwargs: dict[str, Any],
    log_queue: multiprocessing.Queue,  # type: ignore
    log_level: int,
) -> None:
    print(type(action))
    print(type(kwargs))
    print(type(log_queue))
    print(type(log_level))
    child_logger = logging.getLogger()
    child_logger.addHandler(QueueHandler(log_queue))
    child_logger.setLevel(log_level)
    game = get_game_object()
    if hasattr(game, action):
        action_func = getattr(game, action)
        if callable(action_func):
            action_func(**kwargs)


@eel.expose
def action_is_running() -> bool:
    global action_process
    if action_process is None:
        return False
    return action_process.is_alive()


@eel.expose
def stop_action() -> None:
    global action_process
    if action_process is not None and action_process.is_alive():
        logging.warning("Stopping")
        action_process.terminate()
    return None


@eel.expose
def shutdown() -> NoReturn:
    sys.exit(0)
