from collections.abc import Callable

from adb_auto_player.models.decorators import CacheGroup
from adb_auto_player.registries import LRU_CACHE_REGISTRY


def register_cache(*groups: CacheGroup):
    """Decorator to register a function under one or more cache groups."""

    def decorator(func: Callable) -> Callable:
        for group in groups:
            LRU_CACHE_REGISTRY.setdefault(group, []).append(func)
        return func

    return decorator
