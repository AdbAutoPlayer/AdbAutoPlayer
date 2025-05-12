"""Proof of concept for Decorator refactor."""

import argparse
import json
import logging
import pprint
import sys
import time
from enum import StrEnum

from adb_auto_player import Command, ConfigLoader, Game, games
from adb_auto_player.adb import (
    exec_wm_size,
    get_adb_client,
    get_adb_device,
    get_running_app,
    get_screen_resolution,
    is_portrait,
    log_devices,
    wm_size_reset,
)
from adb_auto_player.argparse_formatter_factory import build_argparse_formatter
from adb_auto_player.decorators.register_command import command_registry
from adb_auto_player.decorators.register_game import game_registry
from adb_auto_player.ipc import GameGUIOptions, MenuOption
from adb_auto_player.logging_setup import setup_logging
from adbutils import AdbDevice, AdbError


def _load_games_modules() -> None:
    """Workaround to make static code analysis recognize the games module is used."""
    _ = games.__all__


def _get_commands() -> dict[str, list[Command]]:
    commands: dict[str, list[Command]] = {
        "Generic": [
            Command(
                name="GUIGamesMenu",
                action=_print_gui_games_menu,
            ),
            Command(
                name="WMSizeReset",
                action=wm_size_reset,
            ),
            Command(
                name="WMSize1080x1920",
                action=exec_wm_size,
                kwargs={"resolution": "1080x1920"},
            ),
            Command(
                name="GetRunningGame",
                action=_print_running_game,
            ),
            Command(
                name="Debug",
                action=_print_debug,
            ),
        ]
    }

    for module, game_metadata in game_registry.items():
        game_name = game_metadata.name
        cmds = command_registry.get(module, {})

        if game_name not in commands:
            commands[game_name] = []

        commands[game_name].extend(cmds.values())
    return commands


def _print_gui_games_menu() -> None:
    """Print the menu for the GUI to CLI."""
    print(get_gui_games_menu())


def _print_running_game() -> None:
    """Log the title of the currently running game.

    This function retrieves the title of the game currently running on an
    ADB-connected device, if any. If a game is found, it logs the title with
    an info-level log. If no game is running, it logs a debug message
    indicating the absence of a running game.
    """
    running_game: str | None = _get_running_game()
    if running_game:
        # Need to force debug here for
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug(f"Running game: {running_game}")
    else:
        logging.debug("No running game")


def _get_games() -> list[Game]:
    game_objects = []
    for class_name in games.__all__:
        cls = getattr(games, class_name)
        game_objects.append(cls())
    return game_objects


def _get_running_game() -> str | None:
    """Retrieve the title of the currently running game.

    This function attempts to determine which game is currently running on an
    ADB-connected device. It first acquires the device, then retrieves the
    package name of the running application. It checks this package name against
    the package names of known games. If a match is found, it returns the
    corresponding game's title.

    Returns:
        str | None: The title of the running game, or None if no known game is
        detected.
    """
    try:
        device: AdbDevice = get_adb_device()
        package_name: str | None = get_running_app(device)
        if not package_name:
            return None
        for game in _get_games():
            if any(pn in package_name for pn in game.package_name_substrings):
                return game.get_gui_options().game_title
    except AdbError as e:
        if str(e) == "closed":
            # This error usually happens when you try to initialize an ADB Connection
            # Before the device is ready e.g. emulator is starting
            # Also contains no actionable information so best to hide from Users
            logging.debug("ADB Error: closed")
            return None
        logging.error(f"ADB Error: {e}")
    except Exception as e:
        logging.error(f"{e}")
    return None


def get_gui_games_menu() -> str:
    """Get the menu for the GUI.

    Returns a JSON string containing a list of dictionaries.
    Each dictionary represents a game and contains the following keys:
        - game_title: str
        - config_path: str
        - menu_options: list[MenuOption]
        - constraints: dict[str, Any]

    Used by the Wails GUI to populate the menu.
    """
    menu = []
    for module, game in game_registry.items():
        categories: set[str] = set()
        if game.gui_metadata.categories:
            for value in game.gui_metadata.categories:
                if isinstance(value, StrEnum):
                    categories.add(value.value)
                else:
                    categories.add(value)

        menu_options: list[MenuOption] = []
        commands = command_registry.get(module, {})
        for name, command in commands.items():
            menu_options.append(command.menu_option)

        for menu_option in menu_options:
            if menu_option.category:
                categories.add(menu_option.category)

        options: GameGUIOptions = GameGUIOptions(
            game_title=game.name,
            config_path=game.config_file_path.as_posix(),
            menu_options=menu_options,
            categories=list(categories),
            constraints=game.gui_metadata.config_class.get_constraints(),
        )
        menu.append(options.to_dict())

    return json.dumps(menu)


def main() -> None:
    """Main entry point of the application.

    This function parses the command line arguments, sets up the logging based on
    the output format and log level, and then runs the specified command.
    """
    commands = _get_commands()
    command_names = []
    for category_commands in commands.values():
        for cmd in category_commands:
            command_names.append(cmd.name)

    parser = argparse.ArgumentParser(
        formatter_class=build_argparse_formatter(_get_commands())
    )
    parser.add_argument(
        "command",
        help="Command to run",
        choices=command_names,
    )
    parser.add_argument(
        "--output",
        choices=["json", "terminal", "text", "raw"],
        default="json",
        help="Output format",
    )
    parser.add_argument(
        "--log-level",
        choices=["DISABLE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="DEBUG",
        help="Log level",
    )

    args = parser.parse_args()
    log_level = args.log_level
    if log_level == "DISABLE":
        log_level = 99

    setup_logging(args.output, log_level)

    for category_commands in commands.values():
        for cmd in category_commands:
            if str.lower(cmd.name) == str.lower(args.command):
                if cmd.run() is None:
                    sys.exit(0)
                else:
                    sys.exit(1)
    sys.exit(1)


def _print_debug() -> None:
    logging.info("--- Debug Info Start ---")
    logging.info("--- Main Config ---")
    config = ConfigLoader().main_config
    logging.info(f"Config: {pprint.pformat(config)}")
    logging.info("--- ADB Client ---")
    client = None
    try:
        client = get_adb_client()
        log_devices(client.list(), logging.INFO)
    except Exception as e:
        logging.error(f"Error: {e}")

    device = None
    if client:
        logging.info("--- ADB Device ---")
        try:
            device = get_adb_device(adb_client=client)
        except Exception as e:
            logging.error(f"Error: {e}")

    if device:
        logging.info("--- Device Info ---")
        logging.info(f"Device Serial: {device.serial}")
        logging.info(f"Device Info: {device.info}")
        _ = get_running_app(device)

        logging.info("--- Testing Input Delay ---")
        total_time: float = 0.0
        iterations = 10

        for i in range(iterations):
            start_time = time.time()
            device.click(-1, -1)
            end_time = time.time()

            elapsed_time = (end_time - start_time) * 1000  # convert to milliseconds
            total_time += elapsed_time

        average_time = total_time / iterations
        logging.info(
            "Average time taken to tap screen "
            f"{iterations} times: {average_time:.2f} ms"
        )

        logging.info("--- Device Display ---")
        _ = get_screen_resolution(device)
        _ = is_portrait(device)
        logging.info("--- Test Resize Display ---")
        try:
            exec_wm_size("1080x1920", device)
            logging.info("Set Display Size 1080x1920 - OK")
        except Exception as e:
            logging.error(f"Set Display Size to 1080x1920 - Error: : {e}")
        try:
            wm_size_reset(device)
            logging.info("Reset Display Size - OK")
        except Exception as e:
            logging.error(f"Reset Display Size - Error: {e}")

    logging.info("--- Debug Info End ---")


if __name__ == "__main__":
    main()
    sys.exit(0)
