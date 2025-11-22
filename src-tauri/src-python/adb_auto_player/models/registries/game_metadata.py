"""GameMetadata."""

from dataclasses import dataclass

from ..decorators import GameGUIMetadata


@dataclass
class GameMetadata:
    """Metadata used to describe a Game.

    Attributes:
        name (str): The name of the Game.
        settings_file (str | None): Settings file name.
            None if no Settings are used.
        gui_metadata (GameGUIMetadata | None): Metadata to pass to the GUI.
    """

    name: str
    settings_file: str | None = None
    gui_metadata: GameGUIMetadata | None = None
