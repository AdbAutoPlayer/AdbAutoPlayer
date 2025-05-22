"""Proof of concept for Decorator refactor."""

import argparse
import sys

from adb_auto_player import Command, commands, games
from adb_auto_player.argparse_formatter_factory import build_argparse_formatter
from adb_auto_player.decorators.register_command import command_registry
from adb_auto_player.decorators.register_game import game_registry
from adb_auto_player.logging_setup import setup_logging


def _load_modules() -> None:
    """Workaround to make static code analysis recognize the imports are required."""
    _ = games.__all__
    _ = commands.__all__


def _get_commands() -> dict[str, list[Command]]:
    commands: dict[str, list[Command]] = {}

    for module, cmds in command_registry.items():
        # Check if module has a game registered
        if module in game_registry:
            game_name = game_registry[module].name
        else:
            # do not change this it's a special keyword the GUI uses.
            game_name = "Commands"

        if game_name not in commands:
            commands[game_name] = []

        commands[game_name].extend(cmds.values())

    return commands


def main() -> None:
    """Main entry point of the application.

    This function parses the command line arguments, sets up the logging based on
    the output format and log level, and then runs the specified command.
    """
    cmds = _get_commands()
    command_names = []
    for category_commands in cmds.values():
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

    for category_commands in cmds.values():
        for cmd in category_commands:
            if str.lower(cmd.name) == str.lower(args.command):
                if cmd.run() is None:
                    sys.exit(0)
                else:
                    sys.exit(1)
    sys.exit(1)


if __name__ == "__main__":
    main()
    sys.exit(0)
