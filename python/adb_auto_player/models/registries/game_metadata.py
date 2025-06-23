"""GameMetadata."""

from dataclasses import dataclass
from pathlib import Path

from ..decorators import GameGUIMetadata


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
    config_file_path: Path | None = None
    gui_metadata: GameGUIMetadata | None = None
