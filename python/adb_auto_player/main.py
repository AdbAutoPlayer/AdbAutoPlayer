"""Adb Auto Player Main Module."""

import argparse
import json
import logging
import pprint
import sys
from logging import DEBUG

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
from adb_auto_player.ipc import GameGUIOptions
from adb_auto_player.logging_setup import setup_logging
from adbutils import AdbError
from adbutils._device import AdbDevice


def _get_games() -> list[Game]:
    game_objects = []
    for class_name in games.__all__:
        cls = getattr(games, class_name)
        game_objects.append(cls())
    return game_objects


def main() -> None:
    """Main entry point of the application.

    This function parses the command line arguments, sets up the logging based on the
    output format and log level, and then runs the specified command.
    """
    commands_by_category: dict[str, list[Command]] = _get_commands()
    command_names = []
    for category_commands in commands_by_category.values():
        for cmd in category_commands:
            command_names.append(cmd.name)

    parser = argparse.ArgumentParser(
        formatter_class=build_argparse_formatter(commands_by_category)
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

    for category_commands in commands_by_category.values():
        for cmd in category_commands:
            if str.lower(cmd.name) == str.lower(args.command):
                if cmd.run() is None:
                    sys.exit(0)
                else:
                    sys.exit(1)

    sys.exit(1)


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
    for game in _get_games():
        options: GameGUIOptions = game.get_gui_options()
        menu.append(options.to_dict())

    return json.dumps(menu)


def _get_commands() -> dict[str, list[Command]]:
    """Retrieve a dictionary of categorized CLI commands.

    This function organizes commands into categories, starting with generic commands,
    and extends the categories with game-specific commands based on each game's title.

    Returns:
        dict[str, list[Command]]: Mapped category names to lists of Command objects.
    """
    commands_by_category: dict[str, list[Command]] = {
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

    for game in _get_games():
        game_title = game.get_gui_options().game_title
        if game_title not in commands_by_category:
            commands_by_category[game_title] = []
        commands_by_category[game_title].extend(game.get_cli_menu_commands())

    commands_by_category = {
        category: cmds
        for category, cmds in commands_by_category.items()
        if cmds  # Only keep if list is not empty
    }

    return commands_by_category


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
        logging.getLogger().setLevel(DEBUG)
        logging.debug(f"Running game: {running_game}")
    else:
        logging.debug("No running game")


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


if __name__ == "__main__":
    main()
