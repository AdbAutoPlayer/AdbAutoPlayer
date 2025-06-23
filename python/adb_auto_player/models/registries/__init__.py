"""Models for Registry objects."""

from adb_auto_player.models.decorators.game_gui_metadata import GameGUIMetadata

from .custom_routine_entry import CustomRoutineEntry
from .game_metadata import GameMetadata

__all__ = [
    "CustomRoutineEntry",
    "GameGUIMetadata",
    "GameMetadata",
]
