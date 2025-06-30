"""Provides a registry mechanism for Games.

It defines data structures to describe game configuration and GUI display
metadata, as well as a decorator `@register_game` that associates game
classes with their metadata and stores them in a central registry.

Classes:
    GameGUIMetadata: Contains metadata required by the GUI to configure and
        display the game.
    GameMetadata: Holds overall metadata for a game.

Globals:
    GAME_REGISTRY (dict): A mapping of module keys to `GameMetadata` entries for
        all registered games.

Functions:
    register_game: A decorator used to register game classes and
        populate the `GAME_REGISTRY`.

"""

from pathlib import Path
from types import FunctionType

from adb_auto_player.models.registries import GameGUIMetadata, GameMetadata
from adb_auto_player.registries import GAME_REGISTRY
from adb_auto_player.util import StringHelper


def register_game(
    name: str,
    config_file_path: Path | str | None = None,
    gui_metadata: GameGUIMetadata | None = None,
):
    """Decorator to register a game class in the GAME_REGISTRY.

    Args:
        name (str): Name of the game.
        config_file_path (Path | str | None): Path to the game's configuration file.
        gui_metadata (GameGUIMetadata | None): Metadata for GUI configuration.

    Raises:
        TypeError: If the decorator is used on a non-class object.
    """

    def decorator(cls):
        if isinstance(cls, FunctionType):
            raise TypeError("The @register_game decorator can only be used on classes.")

        module_key = StringHelper.get_game_module(cls.__module__)

        if isinstance(config_file_path, str):
            path_obj = Path(config_file_path)
        else:
            path_obj = config_file_path

        metadata = GameMetadata(
            name=name, config_file_path=path_obj, gui_metadata=gui_metadata
        )
        GAME_REGISTRY[module_key] = metadata
        return cls

    return decorator
