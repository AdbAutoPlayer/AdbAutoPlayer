"""GameGUIMetadata."""

from dataclasses import dataclass
from enum import StrEnum

from adb_auto_player.models.pydantic import TomlSettings


@dataclass
class GameGUIMetadata:
    """Metadata to pass to the GUI for display.

    Attributes:
        settings_class (Type[TomlSettings]): A class that implements the TomlSettings
            interface; used by the GUI to understand how to configure the game.
        categories (list[str | StrEnum] | None): Categories to be displayed in the GUI,
            shown in the specified order.

    """

    settings_class: type[TomlSettings] | None = None
    categories: list[str | StrEnum] | None = None
