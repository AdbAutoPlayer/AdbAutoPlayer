from dataclasses import dataclass


@dataclass
class MenuOption:
    label: str
    args: list[str]
    order: int


@dataclass
class GameGUIOptions:
    game_title: str
    config_path: str
    menu_options: list[MenuOption]
    config_schema: str
    order: int | None = None

    def to_dict(self):
        return {
            "game_title": self.game_title,
            "config_path": self.config_path,
            "menu_options": [
                menu_option.__dict__ for menu_option in self.menu_options
            ],  # Convert MenuOption instances to dicts
            "config_schema": self.config_schema,
            "order": self.order,
        }
