"""ADB Auto Player Games Package (Dynamic)."""

import importlib
import inspect
import pkgutil
import sys

from adb_auto_player.game import Game

__all__ = []


def load_modules():
    """Recursively discover and import all submodules in the `games` package."""
    package = sys.modules[__name__]
    yield package  # Yield the root package itself (optional)

    if not hasattr(package, "__path__"):
        return

    def _load_recursively(pkg):
        for _, module_name, is_pkg in pkgutil.iter_modules(pkg.__path__):
            full_name = f"{pkg.__name__}.{module_name}"
            module = importlib.import_module(full_name)
            yield module
            if is_pkg:
                yield from _load_recursively(module)

    yield from _load_recursively(package)


def is_valid_class(cls):
    """Check if the class is a valid subclass of `Game`."""
    return (
        issubclass(cls, Game)
        and cls is not Game
        and not getattr(cls, "__abstractmethods__", False)
    )


def discover_and_add_games():
    """Discover modules, find valid classes, and add them to the globals."""
    seen = set()
    for module in load_modules():
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if is_valid_class(cls) and name not in seen:
                globals()[name] = cls
                __all__.append(name)
                seen.add(name)


discover_and_add_games()
