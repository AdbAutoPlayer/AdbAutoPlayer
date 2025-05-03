"""ADB Auto Player Games Package (Dynamic)."""

import importlib
import inspect
import pkgutil

from adb_auto_player import Game

__all__ = []


def load_modules():
    """Discover all submodules in the `games` package."""
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f".{module_name}", package=__name__)
        yield module


def is_valid_class(cls):
    """Check if the class is a valid subclass of `Game`."""
    return issubclass(cls, Game) and cls is not Game


def has_required_methods(cls):
    """Check if the class implements the required methods."""
    try:
        instance = cls()

        method_names = ["get_cli_menu_commands", "get_gui_options"]

        for method_name in method_names:
            method = getattr(instance, method_name, None)

            if not callable(method) or method() is None:
                print(f"Class {cls.__name__} failed check for method: {method_name}")
                return False

        return True

    except TypeError as e:
        print(f"Error instantiating class {cls.__name__}: {e}")
        return False


def discover_and_add_games():
    """Discover modules, find valid classes, and add them to the globals."""
    for module in load_modules():
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if is_valid_class(cls) and has_required_methods(cls):
                globals()[name] = cls
                __all__.append(name)


discover_and_add_games()
