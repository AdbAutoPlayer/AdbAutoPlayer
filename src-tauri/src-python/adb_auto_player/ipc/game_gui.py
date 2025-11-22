"""ADB Auto Player Game GUI Module."""

from dataclasses import dataclass

from .menu_option import MenuOption


@dataclass
class GameGUIOptions:
    """Game GUI Options."""

    game_title: str
    menu_options: list[MenuOption]
    categories: list[str]
    settings_file: str | None = None

    def to_dict(self):
        """Convert to dict for JSON serialization."""
        return {
            "game_title": self.game_title,
            "settings_file": self.settings_file,
            "menu_options": [option.to_dict() for option in self.menu_options],
            "categories": self.categories,
        }
