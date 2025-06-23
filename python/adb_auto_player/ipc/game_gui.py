"""ADB Auto Player Game GUI Module."""

from dataclasses import dataclass
from typing import Any, TypeVar

from adb_auto_player.models.commands import MenuItem

from .constraint import ConstraintType


@dataclass
class GameGUIOptions:
    """Game GUI Options."""

    game_title: str
    menu_options: list[MenuItem]
    categories: list[str]
    config_path: str | None = None
    constraints: dict[str, dict[str, ConstraintType]] | None = None

    def to_dict(self):
        """Converts the GameGUIOptions to a dictionary."""
        return {
            "game_title": self.game_title,
            "config_path": self.config_path,
            "menu_options": [menu_option.__dict__ for menu_option in self.menu_options],
            "categories": self.categories,
            "constraints": add_order_key(self.constraints),
        }


T = TypeVar("T", bound=dict[str, Any])


def add_order_key(data: T) -> T:
    """Adds an 'Order' key to maintain key ordering in the Wails App.

    Go does not maintain order for maps.
    """
    if isinstance(data, dict):
        ordered_keys = list(data.keys())

        order = [key for key in ordered_keys if key and key[0].isupper()]

        if order:
            data["Order"] = order

        for key in ordered_keys:
            if isinstance(data[key], dict):
                add_order_key(data[key])

    return data
