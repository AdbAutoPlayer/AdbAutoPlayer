"""GUI Command: fetches the Menu."""

import json

from adb_auto_player.decorators import (
    register_command,
)
from adb_auto_player.registries import GAME_REGISTRY
from adb_auto_player.util import IPCModelConverter


@register_command(
    gui=None,  # We do not want a GUI Button for this
    name="GUIGamesMenu",
)
def _print_gui_games_menu() -> None:
    print(get_gui_games_menu())


def get_gui_games_menu() -> str:
    """Get the menu for the GUI.

    Used by the Wails GUI to populate the menu.
    """
    menu = []
    for module, game in GAME_REGISTRY.items():
        options = IPCModelConverter.convert_game_to_gui_options(module, game)
        menu.append(options.to_dict())

    return json.dumps(menu)
