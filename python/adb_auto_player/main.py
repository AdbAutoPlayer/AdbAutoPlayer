import logging
import sys
import argparse
from typing import NoReturn

from adb_auto_player import logging_setup
from adb_auto_player.command import Command
from adb_auto_player.games.afk_journey.run import AFKJourney


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

    sys.exit(0)


def __get_commands() -> list[Command]:
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
