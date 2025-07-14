"""ADB Auto Player Game GUI Module."""

from dataclasses import dataclass
from typing import Any

from .constraint import ConstraintType
from .menu_option import MenuOption


@dataclass
class GameGUIOptions:
    """Game GUI Options."""

    game_title: str
    menu_options: list[MenuOption]
    categories: list[str]
    config_path: str | None = None
    constraints: dict[str, dict[str, ConstraintType]] | None = None

    def to_dict(self):
        """Convert to dict for JSON serialization."""
        return {
            "game_title": self.game_title,
            "config_path": self.config_path,
            "menu_options": [option.to_dict() for option in self.menu_options],
            "categories": self.categories,
            "constraints": add_order_key(self.constraints),
        }


def add_order_key(data: dict[str, Any]) -> dict[str, Any]:
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
