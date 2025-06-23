"""GameGUIMetadata."""

from dataclasses import dataclass
from enum import StrEnum

from adb_auto_player.models.pydantic import GameConfig


@dataclass
class GameGUIMetadata:
    """Metadata to pass to the GUI for display.

    Attributes:
        config_class (Type[ConfigBase]): A class that implements the ConfigBase
            interface; used by the GUI to understand how to configure the game.
        categories (list[str | StrEnum] | None): Categories to be displayed in the GUI,
            shown in the specified order.

    """

    config_class: type[GameConfig] | None = None
    categories: list[str | StrEnum] | None = None
