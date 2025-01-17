import logging
import sys
from typing import NoReturn

from adb_auto_player import logging_setup
from adb_auto_player.command import Command
from adb_auto_player.games.afk_journey.run import AFKJourney

HELP_COMMANDS = {"help", "-h", "--h", "-help", "--help"}


def get_commands() -> list[Command] | NoReturn:
    commands = []

    afk_journey = AFKJourney()
    commands += afk_journey.get_menu_commands()
    return commands


def show_help():
    logging.info("Available commands:")
    for cmd in get_commands():
        logging.info("\t\t" + cmd.name)


def run_command(cmd: Command) -> NoReturn:
    try:
        cmd.run()
    except Exception as e:
        logging.error(e)
        sys.exit(1)
    sys.exit(0)


def main() -> None:
    if len(sys.argv) != 2:
        logging.error("Usage: cli.exe <command>")
        show_help()
        sys.exit(1)

    command = sys.argv[1]
    if command in HELP_COMMANDS:
        show_help()
        sys.exit(0)

    for cmd in get_commands():
        if str.lower(cmd.name) == str.lower(command):
            run_command(cmd)
    logging.error(f"Unknown command: {command}")
    show_help()
    sys.exit(1)


if __name__ == "__main__":
    logging_setup.setup_json_log_handler(logging.DEBUG)
    logging.getLogger("PIL").setLevel(logging.INFO)
    main()
