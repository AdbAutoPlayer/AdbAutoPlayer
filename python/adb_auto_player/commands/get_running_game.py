"""GUI Command: fetches currently running game."""

import logging

from adb_auto_player import Game, GenericAdbError, GenericAdbUnrecoverableError, games
from adb_auto_player.adb import get_adb_device, get_running_app
from adb_auto_player.decorators.register_command import register_command
from adb_auto_player.decorators.register_game import game_registry
from adbutils import AdbDevice, AdbError


@register_command(
    gui=None,  # We do not want a GUI Button for this
    name="GetRunningGame",
)
def _print_running_game() -> None:
    """Log the title of the currently running game.

    This function retrieves the title of the game currently running on an
    ADB-connected device, if any. If a game is found, it logs the title with
    an info-level log. If no game is running, it logs a debug message
    indicating the absence of a running game.
    """
    running_game: str | None = _get_running_game()
    if running_game:
        # Need to force debug here for
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug(f"Running game: {running_game}")
    else:
        logging.debug("No running game")


def _get_games() -> list[Game]:
    game_objects = []
    for class_name in games.__all__:
        cls = getattr(games, class_name)
        game_objects.append(cls())
    return game_objects


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
        package_name: str | None = get_running_app(device)
        if not package_name:
            return None
        for game_object in _get_games():
            if (
                any(pn in package_name for pn in game_object.package_name_substrings)
                or game_object.package_name == package_name
            ):
                for module, game in game_registry.items():
                    if module in game_object.__module__:
                        return game.name
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
