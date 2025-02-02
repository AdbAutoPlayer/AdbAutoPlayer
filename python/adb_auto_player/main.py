import logging
import sys
import argparse
from typing import NoReturn

from adb_auto_player import logging_setup
from adb_auto_player.command import Command
from adb_auto_player.games.afk_journey.run import AFKJourney


def main() -> None:
    parser = argparse.ArgumentParser(description="AFK Journey")
    parser.add_argument("command", help="Command to run")
    parser.add_argument(
        "--output", choices=["json", "raw"], default="json", help="Output format"
    )

    args = parser.parse_args()
    if args.output == "json":
        logging_setup.setup_json_log_handler(logging.DEBUG)

    for cmd in __get_commands():
        if str.lower(cmd.name) == str.lower(args.command):
            __run_command(cmd)

    sys.exit(0)


def __get_commands() -> list[Command] | NoReturn:
    commands = []

    afk_journey = AFKJourney()
    commands += afk_journey.get_menu_commands()
    return commands


def __run_command(cmd: Command) -> NoReturn:
    try:
        cmd.run()
    except Exception as e:
        logging.error(e)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    logging.getLogger("PIL").setLevel(logging.INFO)
    main()
