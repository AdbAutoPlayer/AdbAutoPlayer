"""ADB Auto Player Commands Package (Dynamic)."""

import importlib
import pkgutil

__all__ = []


def load_command_modules():
    """Import all command modules to ensure decorators are executed."""
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        full_module_name = f"{__name__}.{module_name}"
        module = importlib.import_module(full_module_name)
        __all__.append(module_name)
        yield module


for _ in load_command_modules():
    pass
