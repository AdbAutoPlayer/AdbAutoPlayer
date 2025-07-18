import json
import logging
import sys
from functools import lru_cache

from adb_auto_player import Game, games
from adb_auto_player.adb import get_adb_device, get_running_app
from adb_auto_player.decorators import register_cache, register_command
from adb_auto_player.exceptions import GenericAdbError, GenericAdbUnrecoverableError
from adb_auto_player.ipc import GameGUIOptions
from adb_auto_player.ipc_util import IPCModelConverter
from adb_auto_player.models.decorators import CacheGroup
from adb_auto_player.registries import GAME_REGISTRY
from adbutils import AdbDevice, AdbError


@register_command(
    gui=None,  # We do not want a GUI Button for this
    name="DisplayGUI",
)
def _display_gui() -> None:
    print(_get_running_game_gui())
    sys.stdout.flush()


def _get_running_game_gui() -> str:
    options = _get_game_gui_options()
    running_game = _get_running_game()

    if running_game is not None:
        matching_option = next(
            (opt for opt in options if opt.game_title == running_game), None
        )
        if matching_option is not None:
            return json.dumps(matching_option.to_dict())

    return "{}"


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
        return _get_game_from_package_name(get_running_app(device))
    except (AdbError, GenericAdbError, GenericAdbUnrecoverableError) as e:
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


@lru_cache(maxsize=3)
def _get_game_from_package_name(package_name: str | None) -> str | None:
    if not package_name:
        return None
    for game_object in _get_games():
        if (
            any(pn in package_name for pn in game_object.package_name_substrings)
            or game_object.package_name == package_name
        ):
            for module, game in GAME_REGISTRY.items():
                if module in game_object.__module__:
                    return game.name
    return None


def _get_games() -> list[Game]:
    game_objects = []
    for class_name in games.__all__:
        cls = getattr(games, class_name)
        game_objects.append(cls())
    return game_objects


@register_cache(CacheGroup.GAME_SETTINGS)
@lru_cache(maxsize=1)
def _get_game_gui_options() -> list[GameGUIOptions]:
    """Get the menu for the GUI.

    Used by the Wails GUI to populate the menu.
    """
    menus: list[GameGUIOptions] = []
    for module, game in GAME_REGISTRY.items():
        menus.append(IPCModelConverter.convert_game_to_gui_options(module, game))

    return menus
