"""Tests for IPCModelConverter."""

from enum import StrEnum
from unittest.mock import patch

from adb_auto_player.ipc_util import IPCModelConverter
from adb_auto_player.models.commands import MenuItem
from adb_auto_player.models.registries import GameMetadata


class TestCategory(StrEnum):
    """Test enum for categories."""

    COMBAT = "combat"
    NAVIGATION = "navigation"


class TestIPCModelConverter:
    """Test cases for IPCModelConverter."""

    def test_convert_menu_item_to_menu_option_basic(self):
        """Test basic conversion of MenuItem to MenuOption."""
        menu_item = MenuItem(
            label="Test Command",
            args=["arg1", "arg2"],
            display_in_gui=True,
            category="test",
            tooltip="Test tooltip",
        )
        game_metadata = GameMetadata(name="Test Game")

        result = IPCModelConverter.convert_menu_item_to_menu_option(
            menu_item, game_metadata
        )

        assert result is not None
        assert result.label == "Test Command"
        assert result.args == ["arg1", "arg2"]
        assert result.custom_label is None
        assert result.category == "test"
        assert result.tooltip == "Test tooltip"

    def test_convert_menu_item_to_menu_option_not_display_in_gui(self):
        """Test conversion returns None when display_in_gui is False."""
        menu_item = MenuItem(label="Hidden Command", display_in_gui=False)
        game_metadata = GameMetadata(name="Test Game")

        result = IPCModelConverter.convert_menu_item_to_menu_option(
            menu_item, game_metadata
        )

        assert result is None

    def test_convert_menu_item_to_menu_option_with_empty_args(self):
        """Test conversion with None args."""
        menu_item = MenuItem(label="Test Command", args=None, display_in_gui=True)
        game_metadata = GameMetadata(name="Test Game")

        result = IPCModelConverter.convert_menu_item_to_menu_option(
            menu_item, game_metadata
        )

        assert result is not None
        assert result.args == []

    @patch.object(IPCModelConverter, "_resolve_label_from_settings")
    def test_convert_menu_item_to_menu_option_with_translation(self, mock_resolve):
        """Test conversion with customizable label."""
        mock_resolve.return_value = "Custom Label"

        menu_item = MenuItem(label="Original Label", display_in_gui=True)
        game_metadata = GameMetadata(name="Test Game")

        result = IPCModelConverter.convert_menu_item_to_menu_option(
            menu_item, game_metadata
        )

        assert result is not None
        assert result.label == "Original Label"
        assert result.custom_label == "Custom Label"

    def test_extract_categories_from_game_no_gui_metadata(self):
        """Test category extraction with no GUI metadata."""
        game = GameMetadata(name="Test Game")

        categories = IPCModelConverter._extract_categories_from_game(game)

        assert categories == list()

    @patch("adb_auto_player.registries.COMMAND_REGISTRY")
    def test_get_menu_options_from_commands_empty_module(self, mock_registry):
        """Test getting menu options from non-existent module."""
        mock_registry.get.return_value = {}

        game = GameMetadata(name="Test Game")

        result = IPCModelConverter._get_menu_options_from_commands("NonExistent", game)

        assert result == []

    def test_extract_constraints_from_game_no_gui_metadata(self):
        """Test constraint extraction with no GUI metadata."""
        game = GameMetadata(name="Test Game")

        result = IPCModelConverter._extract_constraints_from_game(game)

        assert result is None

    @patch.object(IPCModelConverter, "_extract_categories_from_game")
    @patch.object(IPCModelConverter, "_build_menu_options")
    @patch.object(IPCModelConverter, "_extract_categories_from_menu_options")
    @patch.object(IPCModelConverter, "_extract_constraints_from_game")
    def test_convert_game_to_gui_options_no_settings_file(
        self,
        mock_extract_constraints,
        mock_extract_menu_categories,
        mock_build_menu,
        mock_extract_game_categories,
    ):
        """Test conversion with no Settings file."""
        # Setup mocks
        mock_extract_game_categories.return_value = list()
        mock_build_menu.return_value = []
        mock_extract_menu_categories.return_value = list()
        mock_extract_constraints.return_value = None

        game = GameMetadata(name="Test Game", settings_file=None)

        result = IPCModelConverter.convert_game_to_gui_options("TestModule", game)

        assert result.settings_file is None

    def test_resolve_label_from_settings_no_label_from_settings(self):
        """Test label resolution when no label_from_settings is set."""
        menu_item = MenuItem(label="Original Label")
        game_metadata = GameMetadata(name="Test Game")

        result = IPCModelConverter._resolve_label_from_settings(
            menu_item, game_metadata
        )

        assert result is None

    def test_resolve_label_from_settings_no_settings_file_path(self):
        """Test label resolution when no Settings file path is set."""
        menu_item = MenuItem(
            label="Original Label", label_from_settings="section.label"
        )
        game_metadata = GameMetadata(name="Test Game", settings_file=None)

        result = IPCModelConverter._resolve_label_from_settings(
            menu_item, game_metadata
        )

        assert result is None

    def test_resolve_label_from_settings_no_gui_metadata(self):
        """Test label resolution when no GUI metadata is present."""
        menu_item = MenuItem(
            label="Original Label", label_from_settings="section.label"
        )
        game_metadata = GameMetadata(
            name="Test Game", settings_file="test.toml", gui_metadata=None
        )

        result = IPCModelConverter._resolve_label_from_settings(
            menu_item, game_metadata
        )

        assert result is None
