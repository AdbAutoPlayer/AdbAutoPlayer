"""Provides a registry mechanism for Custom Routine Choices.

It allows game automation routines to be
registered and looked up dynamically based on their associated label and game module.

Usage:
    Use the `@register_custom_routine_choice(label)` decorator to register a function
    under a specific label, grouped by the game module it belongs to.

The registry is stored in `CUSTOM_ROUTINE_REGISTRY`.
"""

from collections.abc import Callable
from typing import Any

from adb_auto_player.models.registries import CustomRoutineEntry
from adb_auto_player.registries import CUSTOM_ROUTINE_REGISTRY
from adb_auto_player.util import StringHelper


def register_custom_routine_choice(
    label: str,
    kwargs: dict[str, Any] | None = None,
):
    """Registers a function as a custom routine choice under a given label.

    The function will be grouped within the `CUSTOM_ROUTINE_REGISTRY` according
    to the game module it originates from (as determined by `get_game_module`).

    Args:
        label (str): A non-empty label that uniquely identifies the
            function within the module. This will be displayed in the GUI.
        kwargs (dict[str, Any] | None): Optional default keyword arguments to pass to
            the function.

    Returns:
        Callable: A decorator that registers the function and returns it unchanged.

    Raises:
        ValueError: If the label is empty or already registered under the same module.
    """
    if not label:
        raise ValueError("The 'label' parameter is required and cannot be empty.")

    def decorator(func: Callable) -> Callable:
        module_key = StringHelper.get_game_module(func.__module__)
        if module_key not in CUSTOM_ROUTINE_REGISTRY:
            CUSTOM_ROUTINE_REGISTRY[module_key] = {}

        if label in CUSTOM_ROUTINE_REGISTRY[module_key]:
            raise ValueError(
                f"A custom routine choice with the label '{label}' "
                f"is already registered in module '{module_key}'."
            )

        entry = CustomRoutineEntry(func=func, kwargs=kwargs or {})
        CUSTOM_ROUTINE_REGISTRY[module_key][label] = entry
        return func

    return decorator
