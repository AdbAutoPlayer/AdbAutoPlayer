"""Provides a registry mechanism for Custom Routine Choices.

It allows game automation routines to be
registered and looked up dynamically based on their associated label and game module.

Usage:
    Use the `@register_custom_routine_choice(label)` decorator to register a function
    under a specific label, grouped by the game module it belongs to.

The registry is stored in `custom_routine_choice_registry`.
"""

from collections.abc import Callable

from adb_auto_player.util.module_helper import get_game_module

# Nested dictionary: { module_name (e.g., 'AFKJourney'): { label: func } }
custom_routine_choice_registry: dict[str, dict[str, Callable]] = {}


def register_custom_routine_choice(label: str):
    """Registers a function as a custom routine choice under a given label.

    The function will be grouped within the `custom_routine_choice_registry` according
    to the game module it originates from (as determined by `get_game_module`).

    Args:
        label (str): A non-empty label that uniquely identifies the
            function within the module. This will be displayed in the GUI.

    Returns:
        Callable: A decorator that registers the function and returns it unchanged.

    Raises:
        ValueError: If the label is empty or already registered under the same module.
    """
    if not label:
        raise ValueError("The 'label' parameter is required and cannot be empty.")

    def decorator(func: Callable) -> Callable:
        module_key = get_game_module(func.__module__)
        if module_key not in custom_routine_choice_registry:
            custom_routine_choice_registry[module_key] = {}

        if label in custom_routine_choice_registry[module_key]:
            raise ValueError(
                f"A custom routine choice with the label '{label}' "
                f"is already registered in module '{module_key}'."
            )

        custom_routine_choice_registry[module_key][label] = func
        return func

    return decorator
