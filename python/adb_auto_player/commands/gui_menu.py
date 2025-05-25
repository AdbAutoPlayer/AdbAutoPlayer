"""GUI Command: fetches the Menu."""

import json
from enum import StrEnum

from adb_auto_player.decorators.register_command import (
    command_registry,
    register_command,
)
from adb_auto_player.decorators.register_game import game_registry
from adb_auto_player.ipc import GameGUIOptions, MenuOption


@register_command(name="GUIGamesMenu")
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
    for module, game in game_registry.items():
        categories: set[str] = set()
        if game.gui_metadata.categories:
            for value in game.gui_metadata.categories:
                if isinstance(value, StrEnum):
                    categories.add(value.value)
                else:
                    categories.add(value)

        menu_options: list[MenuOption] = []
        commands = command_registry.get(module, {})
        for name, command in commands.items():
            menu_options.append(command.menu_option)

        for menu_option in menu_options:
            if menu_option.category:
                categories.add(menu_option.category)

        options: GameGUIOptions = GameGUIOptions(
            game_title=game.name,
            config_path=game.config_file_path.as_posix(),
            menu_options=menu_options,
            categories=list(categories),
            constraints=game.gui_metadata.config_class.get_constraints(),
        )
        menu.append(options.to_dict())

    return json.dumps(menu)
