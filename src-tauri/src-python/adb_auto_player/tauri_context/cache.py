import functools
import threading
from collections import OrderedDict
from typing import Any
from collections.abc import Callable, Hashable

from .context import TauriContext


def profile_aware_cache(maxsize: int | None = None):
    """Per-profile cache decorator.
    Each profile gets its own cache.
    profile_index=None is used for CLI mode.
    """

    def decorator(func: Callable):
        lock = threading.RLock()
        caches: dict[int | None, OrderedDict[tuple[Hashable, ...], Any]] = {}

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            profile = TauriContext.get_profile_index()
            key = _make_key(args, kwargs)

            with lock:
                cache = caches.setdefault(profile, OrderedDict())

                if key in cache:
                    cache.move_to_end(key)
                    return cache[key]

            # Compute outside lock
            value = func(*args, **kwargs)

            with lock:
                cache = caches.setdefault(profile, OrderedDict())
                cache[key] = value
                cache.move_to_end(key)

                if maxsize is not None and len(cache) > maxsize:
                    cache.popitem(last=False)

            return value

        def cache_clear(profile_index: int | None = None):
            """Clear cache for a specific profile.
            profile_index=None  → clear all profiles
            profile_index=int   → clear only that profile
            """
            with lock:
                if not profile_index:
                    caches.clear()
                    return

                if profile_index in caches:
                    caches[profile_index].clear()

        wrapper.cache_clear = cache_clear
        wrapper._profile_caches = caches

        return wrapper

    return decorator


def _make_key(args, kwargs):
    """Build a hashable key similar to functools.lru_cache."""
    if kwargs:
        # Using a stable marker to separate positional and keyword args
        items = tuple(sorted(kwargs.items()))
        return args + (object(),) + items
    return args
