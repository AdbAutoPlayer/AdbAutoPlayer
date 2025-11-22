import logging
from functools import lru_cache

from adb_auto_player import games
from adb_auto_player.decorators import register_cache
from adb_auto_player.device.adb import AdbController
from adb_auto_player.exceptions import (
    AutoPlayerError,
    GenericAdbError,
    GenericAdbUnrecoverableError,
)
from adb_auto_player.game import Game
from adb_auto_player.ipc import GameGUIOptions
from adb_auto_player.ipc_util import IPCModelConverter
from adb_auto_player.models.decorators import CacheGroup
from adb_auto_player.models.registries import GameMetadata
from adb_auto_player.registries import GAME_REGISTRY
from adb_auto_player.tauri_context import profile_aware_cache


def get_game_gui_options() -> GameGUIOptions | None:
    """Returns menu json string for a game."""
    game = get_game_metadata()
    if game is not None:
        options = _get_game_gui_options()
        return next((opt for opt in options if opt.game_title == game.name), None)

    return None


def get_game_metadata() -> GameMetadata | None:
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
        return _get_game_metadata_from_package_name(AdbController().get_running_app())
    except (GenericAdbError, GenericAdbUnrecoverableError) as e:
        if str(e) == "closed":
            # This error usually happens when you try to initialize an ADB Connection
            # Before the device is ready e.g. emulator is starting
            # Also contains no actionable information so best to hide from Users
            logging.debug("ADB Error: closed")
            return None
        raise AutoPlayerError(f"ADB Error: {e}")


@lru_cache(maxsize=3)
def _get_game_metadata_from_package_name(
    package_name: str | None,
) -> GameMetadata | None:
    if not package_name:
        return None
    for game_object in _get_games():
        if any(pn in package_name for pn in game_object.package_name_prefixes):
            for module, game in GAME_REGISTRY.items():
                if module in game_object.__module__:
                    return game
    return None


def _get_games() -> list[Game]:
    game_objects = []
    for class_name in games.__all__:
        cls = getattr(games, class_name)
        game_objects.append(cls())
    return game_objects


@register_cache(CacheGroup.GAME_SETTINGS)
@profile_aware_cache(maxsize=1)
def _get_game_gui_options() -> list[GameGUIOptions]:
    """Get the menu for the GUI.

    Used by the Wails GUI to populate the menu.
    """
    menus: list[GameGUIOptions] = []
    for module, game in GAME_REGISTRY.items():
        menus.append(IPCModelConverter.convert_game_to_gui_options(module, game))

    return menus
