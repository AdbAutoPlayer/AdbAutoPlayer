"""IPC Model Converter."""

from enum import StrEnum

from adb_auto_player.ipc import GameGUIOptions, MenuOption
from adb_auto_player.models.commands import MenuItem
from adb_auto_player.models.registries import GameMetadata
from adb_auto_player.registries import COMMAND_REGISTRY
from adb_auto_player.settings import SettingsLoader

from .ipc_constraint_extractor import IPCConstraintExtractor


class IPCModelConverter:
    """Util class for converting from and to IPC models."""

    @staticmethod
    def convert_menu_item_to_menu_option(
        menu_item: MenuItem,
        game_metadata: GameMetadata,
    ) -> MenuOption | None:
        """Convert MenuItem to MenuOption for GUI IPC."""
        if not menu_item.display_in_gui:
            return None

        label = menu_item.label

        return MenuOption(
            label=label,
            args=menu_item.args or [],
            custom_label=IPCModelConverter._resolve_label_from_settings(
                menu_item,
                game_metadata,
            ),
            category=menu_item.category,
            tooltip=menu_item.tooltip,
        )

    @staticmethod
    def convert_game_to_gui_options(
        module: str,
        game: GameMetadata,
    ) -> GameGUIOptions:
        """Convert GameMetadata to GameGUIOptions for GUI IPC."""
        categories = IPCModelConverter._extract_categories_from_game(game)
        menu_options = IPCModelConverter._build_menu_options(module, game)
        categories_from_menu = IPCModelConverter._extract_categories_from_menu_options(
            menu_options
        )
        categories = list(dict.fromkeys(categories + categories_from_menu))
        constraints = IPCModelConverter._extract_constraints_from_game(game)

        return GameGUIOptions(
            game_title=game.name,
            settings_file=game.settings_file,
            menu_options=menu_options,
            categories=list(categories),
            constraints=constraints,
        )

    @staticmethod
    def _extract_categories_from_game(game: GameMetadata) -> list[str]:
        """Extract categories from game metadata, preserving order and uniqueness."""
        categories: dict[str, None] = {}

        if game.gui_metadata and game.gui_metadata.categories:
            for value in game.gui_metadata.categories:
                key = value.value if isinstance(value, StrEnum) else value
                categories[key] = None  # insertion order is preserved

        return list(categories.keys())

    @staticmethod
    def _build_menu_options(module: str, game: GameMetadata) -> list[MenuOption]:
        """Build menu options from game and common commands."""
        menu_options: list[MenuOption] = []
        menu_options.extend(
            IPCModelConverter._get_menu_options_from_commands(module, game)
        )
        menu_options.extend(
            IPCModelConverter._get_menu_options_from_commands("Commands", game)
        )

        return menu_options

    @staticmethod
    def _get_menu_options_from_commands(
        module: str, game: GameMetadata
    ) -> list[MenuOption]:
        """Get menu options from commands in a specific module."""
        menu_options: list[MenuOption] = []

        for name, command in COMMAND_REGISTRY.get(module, {}).items():
            if command.menu_item.display_in_gui:
                menu_option = IPCModelConverter.convert_menu_item_to_menu_option(
                    command.menu_item,
                    game,
                )
                if menu_option:
                    menu_options.append(menu_option)

        return menu_options

    @staticmethod
    def _extract_categories_from_menu_options(
        menu_options: list[MenuOption],
    ) -> list[str]:
        """Extract categories from menu options, preserving order and uniqueness."""
        categories: dict[str, None] = {}

        for menu_option in menu_options:
            if menu_option.category:
                categories[menu_option.category] = None  # Insert while preserving order

        return list(categories.keys())

    @staticmethod
    def _extract_constraints_from_game(game: GameMetadata) -> dict | None:
        """Extract constraints from game metadata."""
        if game.gui_metadata and game.gui_metadata.settings_class:
            return IPCConstraintExtractor.get_constraints_from_model(
                game.gui_metadata.settings_class
            )
        return None

    @staticmethod
    def _resolve_label_from_settings(
        menu_item: MenuItem,
        game_metadata: GameMetadata,
    ) -> str | None:
        if (
            not menu_item.label_from_settings
            or not game_metadata.settings_file
            or not game_metadata.gui_metadata
            or not game_metadata.gui_metadata.settings_class
        ):
            return None

        try:
            settings = game_metadata.gui_metadata.settings_class.from_toml(
                SettingsLoader.settings_dir() / game_metadata.settings_file
            )
        except Exception:
            return None

        if not settings:
            return None

        path_parts = menu_item.label_from_settings.split(".")
        current = settings

        try:
            for part in path_parts:
                current = getattr(current, part)

            if current:
                return str(current)
        except AttributeError:
            pass

        return None
