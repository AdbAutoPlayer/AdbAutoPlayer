"""Provides a registry mechanism for Games.

It defines data structures to describe game configuration and GUI display
metadata, as well as a decorator `@register_game` that associates game
classes with their metadata and stores them in a central registry.

Classes:
    GameGUIMetadata: Contains metadata required by the GUI to configure and
        display the game.
    GameMetadata: Holds overall metadata for a game.

Globals:
    game_registry (dict): A mapping of module keys to `GameMetadata` entries for
        all registered games.

Functions:
    register_game: A decorator used to register game classes and
        populate the `game_registry`.

"""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import FunctionType

from adb_auto_player import ConfigBase
from adb_auto_player.util.module_helper import get_game_module


@dataclass
class GameGUIMetadata:
    """Metadata to pass to the GUI for display.

    Attributes:
        config_class (Type[ConfigBase]): A class that implements the ConfigBase
            interface; used by the GUI to understand how to configure the game.
        categories (list[str | StrEnum] | None): Categories to be displayed in the GUI,
            shown in the specified order.

    """

    config_class: type[ConfigBase]
    categories: list[str | StrEnum] | None = None


@dataclass
class GameMetadata:
    """Metadata used to describe a Game.

    Attributes:
        name (str): The name of the Game.
        config_file_path (Path): Path to the configuration file.
            None if no config file is used.
        gui_metadata (GameGUIMetadata): Metadata to pass to the GUI.
    """

    name: str
    config_file_path: Path
    gui_metadata: GameGUIMetadata


game_registry: dict[str, GameMetadata] = {}


def register_game(
    name: str, config_file_path: Path | str, gui_metadata: GameGUIMetadata
):
    """Decorator to register a game class in the game_registry.

    Args:
        name (str): Name of the game.
        config_file_path (Path | str): Path to the game's configuration file.
        gui_metadata (GameGUIMetadata): Metadata for GUI configuration.

    Raises:
        TypeError: If the decorator is used on a non-class object.
    """

    def decorator(cls):
        if isinstance(cls, FunctionType):
            raise TypeError("The @register_game decorator can only be used on classes.")

        module_key = get_game_module(cls.__module__)

        if isinstance(config_file_path, str):
            path_obj = Path(config_file_path)
        else:
            path_obj = config_file_path

        metadata = GameMetadata(
            name=name, config_file_path=path_obj, gui_metadata=gui_metadata
        )
        game_registry[module_key] = metadata
        return cls

    return decorator
