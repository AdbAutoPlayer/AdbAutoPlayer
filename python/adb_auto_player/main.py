"""Main module."""

import logging
import sys
from functools import lru_cache

import uvicorn
from adb_auto_player import commands, games
from adb_auto_player.cli import ArgparseHelper
from adb_auto_player.log import setup_logging
from adb_auto_player.models.commands import Command
from adb_auto_player.registries import COMMAND_REGISTRY, GAME_REGISTRY
from adb_auto_player.server import create_fastapi_server
from adb_auto_player.settings import ConfigLoader
from adb_auto_player.util import DevHelper, Execute


def _load_modules() -> None:
    """Workaround to make static code analysis recognize the imports are required."""
    _ = games.__all__
    _ = commands.__all__


@lru_cache(maxsize=1)
def _get_commands() -> dict[str, list[Command]]:
    cmds: dict[str, list[Command]] = {}
    for module, registered_commands in COMMAND_REGISTRY.items():
        if module in GAME_REGISTRY:
            game_name = GAME_REGISTRY[module].name
        else:
            game_name = "Commands"
        if game_name not in cmds:
            cmds[game_name] = []
        cmds[game_name].extend(registered_commands.values())
    return cmds


def main() -> None:
    """Main entry point of the application.

    This function parses the command line arguments, sets up the logging based on
    the output format and log level, and then runs the specified command.
    """
    parser = ArgparseHelper.build_argument_parser(_get_commands())
    args = parser.parse_args()
    if args.server:
        app = create_fastapi_server(_get_commands())
        advanced_settings = ConfigLoader.general_settings().advanced
        uvicorn.run(
            app,
            host=advanced_settings.auto_player_host,
            port=advanced_settings.auto_player_port,
        )
        sys.exit(0)

    if not args.command:
        parser.error("the following arguments are required: command")

    setup_logging(args.output, ArgparseHelper.get_log_level_from_args(args))
    DevHelper.log_is_main_up_to_date()

    e = Execute.find_command_and_execute(args.command, _get_commands())
    if isinstance(e, BaseException):
        logging.error(e, exc_info=True)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
    sys.exit(0)
