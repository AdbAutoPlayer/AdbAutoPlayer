import json
import logging
import sys
import argparse
from typing import NoReturn

import adb_auto_player.adb
from adb_auto_player import logging_setup
from adb_auto_player.command import Command
from adb_auto_player.game import Game
from adb_auto_player.games.afk_journey.main import AFKJourney
from adb_auto_player.games.infinity_nikki.main import InfinityNikki


def __get_games() -> list[Game]:
    return [
        AFKJourney(),
        InfinityNikki(),
    ]


def main() -> None:
    commands = __get_commands()
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
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="DEBUG",
        help="Log level",
    )

    args = parser.parse_args()
    match args.output:
        case "json":
            logging_setup.setup_json_log_handler(args.log_level)
        case "text":
            logging_setup.setup_text_log_handler(args.log_level)
        case _:
            logging.getLogger().setLevel(args.log_level)

    for cmd in commands:
        if str.lower(cmd.name) == str.lower(args.command):
            __run_command(cmd)

    sys.exit(1)


def get_gui_games_menu() -> str:
    menu = []

    for game in __get_games():
        options = game.get_gui_options()
        menu.append(options.to_dict())

    return json.dumps(menu)


def __get_commands() -> list[Command]:
    commands = [
        Command(
            name="GUIGamesMenu",
            action=__print_gui_games_menu,
        ),
        Command(
            name="WMSizeReset",
            action=adb_auto_player.adb.wm_size_reset,
        ),
        Command(
            name="GetRunningGame",
            action=__print_running_game,
        ),
    ]

    for game in __get_games():
        commands += game.get_cli_menu_commands()

    return commands


def __print_gui_games_menu() -> None:
    print(get_gui_games_menu())
    return None


def __print_running_game() -> None:
    print(__get_running_game(), end="")
    return None


def __get_running_game() -> str:
    logging.disable(logging.CRITICAL)
    try:
        device = adb_auto_player.adb.get_device()
        package_name = adb_auto_player.adb.get_running_app(device)
        for game in __get_games():
            if package_name in game.package_names:
                return game.get_gui_options().game_title
    except Exception:
        pass
    return ""


def __run_command(cmd: Command) -> NoReturn:
    try:
        cmd.run()
    except Exception as e:
        logging.error(f"{e}")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    logging.getLogger("PIL").setLevel(logging.INFO)
    main()
