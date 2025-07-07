"""Provides a registry mechanism for Commands.

Each command can optionally include GUI metadata for display on the GUI.

The commands are stored in a nested dictionary `COMMAND_REGISTRY` with the structure:
    { module_name (e.g., 'AFKJourney'): { command_name: Command } }

Use the `@register_command()` decorator to register a function as a command.
"""

from collections.abc import Callable
from enum import StrEnum
from typing import Any

from adb_auto_player.models.commands import Command, MenuItem
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.registries import COMMAND_REGISTRY
from adb_auto_player.util import StringHelper


def register_command(
    gui: GUIMetadata | None = None,
    name: str | None = None,
    kwargs: dict[str, Any] | None = None,
):
    """Decorator to register a function as a command associated with a game module.

    Optionally includes metadata for rendering the command in a GUI menu,
    and supports passing default keyword arguments to the Command object.

    Args:
        gui (GUIMetadata | None): Optional GUI metadata for display in menus.
        name (str | None): Optional explicit CLI arg name for the command. If not
            provided, a default name of 'module_name.function_name' is used.
        kwargs (dict[str, Any] | None): Optional default keyword arguments to pass to
            the function.

    Returns:
        Callable: A decorator that registers the function as a Command and returns it.

    Raises:
        ValueError: If the command name is already registered for the module.
    """

    def decorator(func: Callable):
        try:
            module_key = StringHelper.get_game_module(func.__module__)
        except ValueError:
            module_key = (
                "Commands"  # do not change this it's a special keyword the GUI uses.
            )
        if module_key not in COMMAND_REGISTRY:
            COMMAND_REGISTRY[module_key] = {}

        resolved_name = name or f"{module_key}.{func.__name__}"

        if any(char.isspace() for char in resolved_name):
            raise ValueError(
                f"Command name '{resolved_name}' cannot contain whitespace."
            )

        if resolved_name in COMMAND_REGISTRY[module_key]:
            raise ValueError(f"Command '{resolved_name}' is already registered.")

        menu_item = None
        if gui:
            category_value = gui.category
            if isinstance(gui.category, StrEnum):
                category_value = gui.category.value
            menu_item = MenuItem(
                label=gui.label,
                label_from_config=gui.label_from_config,
                category=category_value,
                tooltip=gui.tooltip,
            )

        COMMAND_REGISTRY[module_key][resolved_name] = Command(
            name=resolved_name,
            action=func,
            kwargs=kwargs or {},
            menu_item=menu_item,
        )
        return func

    return decorator
