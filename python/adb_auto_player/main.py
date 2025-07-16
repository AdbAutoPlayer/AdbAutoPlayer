"""Main module."""

import argparse
import sys

from adb_auto_player import commands, games
from adb_auto_player.cli import build_argparse_formatter
from adb_auto_player.log import setup_logging
from adb_auto_player.models.commands import Command
from adb_auto_player.registries import COMMAND_REGISTRY, GAME_REGISTRY
from adb_auto_player.server import start_server
from adb_auto_player.util import DevHelper, Execute


def _load_modules() -> None:
    """Workaround to make static code analysis recognize the imports are required."""
    _ = games.__all__
    _ = commands.__all__


def _get_commands() -> dict[str, list[Command]]:
    cmds: dict[str, list[Command]] = {}

    for module, registered_commands in COMMAND_REGISTRY.items():
        # Check if module has a game registered
        if module in GAME_REGISTRY:
            game_name = GAME_REGISTRY[module].name
        else:
            # do not change this it's a special keyword the GUI uses.
            game_name = "Commands"

        if game_name not in registered_commands:
            cmds[game_name] = []

        cmds[game_name].extend(registered_commands.values())

    return cmds


def main() -> None:
    """Main entry point of the application.

    This function parses the command line arguments, sets up the logging based on
    the output format and log level, and then runs the specified command.
    """
    cmds = _get_commands()
    parser = argparse.ArgumentParser(
        formatter_class=build_argparse_formatter(_get_commands())
    )
    parser.add_argument("--ws-port", type=int, default=8765)

    command_names = ["StartServer"]
    for category_commands in cmds.values():
        for cmd in category_commands:
            command_names.append(cmd.name)

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

    DevHelper.log_is_main_up_to_date()

    if args.command == "StartServer":
        start_server(args.ws_port)
        sys.exit(0)

    for category_commands in cmds.values():
        for cmd in category_commands:
            if str.lower(cmd.name) == str.lower(args.command):
                if Execute.command(cmd) is None:
                    sys.exit(0)
                else:
                    sys.exit(1)
    sys.exit(1)


if __name__ == "__main__":
    main()
    sys.exit(0)
