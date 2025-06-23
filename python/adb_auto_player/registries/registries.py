"""See __init__.py."""

from adb_auto_player.models.commands import Command
from adb_auto_player.models.registries import CustomRoutineEntry, GameMetadata

# Nested dictionary: { module_name (e.g., 'AFKJourney'): { name: Command } }
COMMAND_REGISTRY: dict[str, dict[str, Command]] = {}

# { module_name (e.g., 'AFKJourney'): { label: CustomRoutineEntry} } }
CUSTOM_ROUTINE_REGISTRY: dict[str, dict[str, CustomRoutineEntry]] = {}

GAME_REGISTRY: dict[str, GameMetadata] = {}
