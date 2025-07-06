"""ADB Auto Player Game GUI Module."""

from dataclasses import dataclass
from typing import Any, TypeVar

from adb_auto_player.models.commands import MenuItem

from ..registries import GAME_REGISTRY
from ..util import ConfigLoader
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
            "menu_options": self._get_formatted_menu_options(),
            "categories": self.categories,
            "constraints": add_order_key(self.constraints),
        }

    def _get_formatted_menu_options(self) -> list[dict[str, Any]]:
        if self.config_path is None:
            return [menu_option.__dict__ for menu_option in self.menu_options]

        config = None
        for game in GAME_REGISTRY.values():
            if (
                game.name == self.game_title
                and game.gui_metadata
                and game.gui_metadata.config_class
                and game.config_file_path
            ):
                try:
                    config = game.gui_metadata.config_class.from_toml(
                        ConfigLoader.games_dir() / game.config_file_path
                    )
                    break
                except Exception:
                    break

        if config is None:
            return [menu_option.__dict__ for menu_option in self.menu_options]
        formatted_options = []
        for menu_option in self.menu_options:
            option_dict = menu_option.__dict__.copy()

            if (
                hasattr(menu_option, "label_from_config")
                and menu_option.label_from_config
            ):
                path_parts = menu_option.label_from_config.split(".")
                current = config

                try:
                    for part in path_parts:
                        current = getattr(current, part)

                    if current:
                        option_dict["label"] = current
                except AttributeError:
                    pass

            formatted_options.append(option_dict)

        return formatted_options


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
