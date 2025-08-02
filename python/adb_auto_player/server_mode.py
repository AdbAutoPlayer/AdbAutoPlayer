"""This is used for GUI background tasks like checking what game is running."""

import argparse
import logging
import sys

from adb_auto_player.cli import ArgparseHelper
from adb_auto_player.log import setup_logging
from adb_auto_player.models.commands import Command
from adb_auto_player.models.decorators import CacheGroup
from adb_auto_player.registries import LRU_CACHE_REGISTRY
from adb_auto_player.util import Execute


def server_mode(commands: dict[str, list[Command]]):
    """Run in server mode for continuous communication with GUI."""
    setup_logging("json", "DEBUG")
    parser = ArgparseHelper.build_argument_parser(commands, exit_on_error=False)

    for line in sys.stdin:
        string = line.strip().split()

        if string == "general-settings-updated":
            _on_general_settings_updated()
            continue

        if string == "game-settings-updated":
            _on_game_settings_updated()
            continue

        try:
            args = parser.parse_args(string)
            logging.getLogger().setLevel(ArgparseHelper.get_log_level_from_args(args))

            if Execute.find_command_and_execute(args.command, commands):
                continue

            logging.error(f"Unrecognized Task: {string}")
        except argparse.ArgumentError:
            logging.error(f"Unrecognized Task: {string}")


def _on_game_settings_updated() -> None:
    _clear_cache(CacheGroup.GAME_SETTINGS)
    _print_ok()


def _on_general_settings_updated() -> None:
    _clear_cache(CacheGroup.GENERAL_SETTINGS)
    _clear_cache(CacheGroup.ADB)
    _print_ok()


def _print_ok() -> None:
    print("ok")
    sys.stdout.flush()


def _clear_cache(group: CacheGroup) -> None:
    for func in LRU_CACHE_REGISTRY.get(group, []):
        if hasattr(func, "cache_clear"):
            func.cache_clear()
