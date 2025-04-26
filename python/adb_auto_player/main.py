"""Adb Auto Player Main Module."""

import argparse
import json
import logging
import pprint
import sys
from logging import DEBUG
from typing import NoReturn

from adb_auto_player import Command, ConfigLoader, Game
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
from adb_auto_player.games import (
    AFKJourney,
    AvatarRealmsCollide,
    InfinityNikki,
    PlayStore,
)
from adb_auto_player.ipc import GameGUIOptions
from adb_auto_player.logging_setup import setup_json_log_handler, setup_text_log_handler
from adbutils import AdbError
from adbutils._device import AdbDevice


def _get_games() -> list[Game]:
    return [
        AFKJourney(),
        AvatarRealmsCollide(),
        InfinityNikki(),
        PlayStore(),
    ]


def main() -> None:
    """Main entry point of the application.

    This function parses the command line arguments, sets up the logging based on the
    output format and log level, and then runs the specified command.
    """
    commands: list[Command] = _get_commands()
    command_names = []
    for cmd in commands:
        command_names.append(cmd.name)

    parser = argparse.ArgumentParser(description="AFK Journey")
    parser.add_argument(
        "command",
        help="Command to run",
        choices=command_names,
    )
    parser.add_argument(
        "--output",
        choices=["json", "text", "raw"],
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
    match args.output:
        case "json":
            setup_json_log_handler(log_level)
        case "text":
            setup_text_log_handler(log_level)
        case _:
            logging.getLogger().setLevel(log_level)

    for cmd in commands:
        if str.lower(cmd.name) == str.lower(args.command):
            _run_command(cmd)

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


def _get_commands() -> list[Command]:
    """Retrieve a list of CLI commands.

    This function compiles a list of commands for the application, including
    GUI-related commands and game-specific commands. It starts with a set of
    predefined commands, such as displaying the GUI games menu, resetting the
    window size, and getting the running game information. It then extends this
    list by fetching additional commands from each game instance.

    Returns:
        list[Command]: A list of Command objects representing available CLI
        commands for the application.
    """
    commands: list[Command] = [
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
        Command(name="Debug", action=_print_debug),
    ]

    for game in _get_games():
        commands += game.get_cli_menu_commands()

    return commands


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


def _run_command(cmd: Command) -> NoReturn:
    """Execute a command and handle exceptions.

    This function runs the specified command and manages any exceptions
    that occur during execution. If an exception occurs, it logs the error
    message and exits the program with a status of 1. If the command runs
    successfully, it exits the program with a status of 0.

    Args:
        cmd (Command): The command to execute.

    Raises:
        SystemExit: Exits with status 1 if an exception occurs, or status 0
        if the command completes successfully.
    """
    try:
        cmd.run()
    except Exception as e:
        logging.error(f"{e}")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
