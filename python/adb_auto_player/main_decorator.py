"""Proof of concept for Decorator refactor."""

from adb_auto_player import games
from adb_auto_player.decorators.register_command import command_registry
from adb_auto_player.decorators.register_custom_routine_choice import (
    custom_routine_choice_registry,
)
from adb_auto_player.util.module_helper import get_game_module

if __name__ == "__main__":
    print(f"Games: {games.__all__}")
    print()

    print(f"Command Registry: {command_registry}")
    print()

    print(f"Custom Routine Choice Registry: {custom_routine_choice_registry}")
    print()

    for class_name in games.__all__:
        cls = getattr(games, class_name)
        module = cls.__module__
        game_module = get_game_module(module)
        print(
            f"Game: '{class_name}'; Module: '{module}'; Game Module: '{game_module}'; "
        )
        print(f"Commands: {command_registry.get(game_module, {})}")
        print(
            "Custom Routine Choices: "
            f"{custom_routine_choice_registry.get(game_module, {})}"
        )

        print()
