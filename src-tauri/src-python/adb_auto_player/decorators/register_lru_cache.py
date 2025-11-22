from collections.abc import Callable

from adb_auto_player.models.decorators import CacheGroup
from adb_auto_player.registries import CACHE_REGISTRY


def register_cache(*groups: CacheGroup, profile_aware: bool = True):
    """Decorator to register a function's cache under one or more groups.

    If profile_aware=True, _cache_clear will call func.cache_clear(profile_index)
    Otherwise, it will call func.cache_clear()
    """

    def decorator(func: Callable) -> Callable:
        for group in groups:
            CACHE_REGISTRY.setdefault(group, []).append((func, profile_aware))
        return func

    return decorator
