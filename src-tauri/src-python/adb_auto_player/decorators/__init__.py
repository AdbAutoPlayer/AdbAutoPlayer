"""Decorators."""

from .register_command import register_command
from .register_custom_routine_choice import register_custom_routine_choice
from .register_game import register_game
from .register_lru_cache import register_cache

__all__ = [
    "register_cache",
    "register_command",
    "register_custom_routine_choice",
    "register_game",
]
