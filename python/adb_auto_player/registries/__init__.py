"""Commands, Games and CustomRoutines.

The modules here should never have dependencies except models.
"""

from .registries import (
    COMMAND_REGISTRY,
    CUSTOM_ROUTINE_REGISTRY,
    GAME_REGISTRY,
    LRU_CACHE_REGISTRY,
)

__all__ = [
    "COMMAND_REGISTRY",
    "CUSTOM_ROUTINE_REGISTRY",
    "GAME_REGISTRY",
    "LRU_CACHE_REGISTRY",
]
