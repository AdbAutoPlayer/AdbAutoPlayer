"""GUI Command: fetches the Menu."""

import json
from enum import StrEnum

from adb_auto_player.decorators import (
    register_command,
)
from adb_auto_player.ipc import GameGUIOptions
from adb_auto_player.models.commands import MenuItem
from adb_auto_player.registries import COMMAND_REGISTRY, GAME_REGISTRY
from adb_auto_player.util import IPCConstraintExtractor


@register_command(
    gui=None,  # We do not want a GUI Button for this
    name="GUIGamesMenu",
)
def _print_gui_games_menu() -> None:
    print(get_gui_games_menu())


def get_gui_games_menu() -> str:
    """Get the menu for the GUI.

    Returns a JSON string containing a list of dictionaries.
    Each dictionary represents a game and contains the following keys:
        - game_title: str
        - config_path: str
        - menu_options: list[MenuOption]
        - constraints: dict[str, Any]

    Used by the Wails GUI to populate the menu.
    """
    menu = []
    for module, game in GAME_REGISTRY.items():
        categories: set[str] = set()
        if game.gui_metadata and game.gui_metadata.categories:
            for value in game.gui_metadata.categories:
                if isinstance(value, StrEnum):
                    categories.add(value.value)
                else:
                    categories.add(value)

        menu_options: list[MenuItem] = []
        for name, command in COMMAND_REGISTRY.get(module, {}).items():
            if command.menu_option.display_in_gui:
                menu_options.append(command.menu_option)

        # add common commands
        for name, command in COMMAND_REGISTRY.get("Commands", {}).items():
            if command.menu_option.display_in_gui:
                menu_options.append(command.menu_option)

        for menu_option in menu_options:
            if menu_option.category:
                categories.add(menu_option.category)

        options: GameGUIOptions = GameGUIOptions(
            game_title=game.name,
            config_path=(
                game.config_file_path.as_posix() if game.config_file_path else None
            ),
            menu_options=menu_options,
            categories=list(categories),
            constraints=(
                IPCConstraintExtractor.get_constraints_from_model(
                    game.gui_metadata.config_class
                )
                if game.gui_metadata and game.gui_metadata.config_class
                else None
            ),
        )
        menu.append(options.to_dict())

    return json.dumps(menu)
