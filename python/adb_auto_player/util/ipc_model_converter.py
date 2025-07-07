"""IPC Model Converter."""

from enum import StrEnum

from adb_auto_player.ipc import GameGUIOptions, MenuOption
from adb_auto_player.models.commands import MenuItem
from adb_auto_player.models.registries import GameMetadata
from adb_auto_player.registries import COMMAND_REGISTRY
from adb_auto_player.util import IPCConstraintExtractor

from .config_loader import ConfigLoader


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
        translated = False
        resolved_label = IPCModelConverter._resolve_label_from_config(
            menu_item,
            game_metadata,
        )

        if resolved_label:
            label = resolved_label
            translated = True

        return MenuOption(
            label=label,
            args=menu_item.args or [],
            translated=translated,
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
        categories.update(
            IPCModelConverter._extract_categories_from_menu_options(menu_options)
        )
        constraints = IPCModelConverter._extract_constraints_from_game(game)

        return GameGUIOptions(
            game_title=game.name,
            config_path=(
                game.config_file_path.as_posix() if game.config_file_path else None
            ),
            menu_options=menu_options,
            categories=list(categories),
            constraints=constraints,
        )

    @staticmethod
    def _extract_categories_from_game(game: GameMetadata) -> set[str]:
        """Extract categories from game metadata."""
        categories: set[str] = set()

        if game.gui_metadata and game.gui_metadata.categories:
            for value in game.gui_metadata.categories:
                if isinstance(value, StrEnum):
                    categories.add(value.value)
                else:
                    categories.add(value)

        return categories

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
    ) -> set[str]:
        """Extract categories from menu options."""
        categories: set[str] = set()

        for menu_option in menu_options:
            if menu_option.category:
                categories.add(menu_option.category)

        return categories

    @staticmethod
    def _extract_constraints_from_game(game: GameMetadata) -> dict | None:
        """Extract constraints from game metadata."""
        if game.gui_metadata and game.gui_metadata.config_class:
            return IPCConstraintExtractor.get_constraints_from_model(
                game.gui_metadata.config_class
            )
        return None

    @staticmethod
    def _resolve_label_from_config(
        menu_item: MenuItem,
        game_metadata: GameMetadata,
    ) -> str | None:
        if (
            not menu_item.label_from_config
            or not game_metadata.config_file_path
            or not game_metadata.gui_metadata
            or not game_metadata.gui_metadata.config_class
        ):
            return None

        try:
            config = game_metadata.gui_metadata.config_class.from_toml(
                ConfigLoader.games_dir() / game_metadata.config_file_path
            )
        except Exception:
            return None

        if not config:
            return None

        path_parts = menu_item.label_from_config.split(".")
        current = config

        try:
            for part in path_parts:
                current = getattr(current, part)

            if current:
                return str(current)
        except AttributeError:
            pass

        return None
