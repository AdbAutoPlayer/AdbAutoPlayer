import pytest
from adb_auto_player.util import get_game_module


class TestGetGameModule:
    """Test class for get_game_module utility function."""

    def test_valid_game_module(self):
        """Test that valid game modules are correctly extracted."""
        assert get_game_module("root.games.poker") == "poker"

    def test_empty_module_path(self):
        """Test that empty or whitespace-only strings raise ValueError."""
        with pytest.raises(
            ValueError, match="Module path cannot be empty or just whitespace"
        ):
            get_game_module("")

        with pytest.raises(ValueError):
            get_game_module("   ")

    def test_module_path_too_short(self):
        """Test that module paths shorter than 3 parts raise ValueError."""
        with pytest.raises(ValueError, match="is too short"):
            get_game_module("games")

        with pytest.raises(ValueError):
            get_game_module("just.two")

    def test_missing_games_part(self):
        """Test that module paths without 'games' as second part raise ValueError."""
        with pytest.raises(ValueError, match="Expected 'games' as the second part"):
            get_game_module("root.notgames.poker")

        with pytest.raises(ValueError):
            get_game_module("games.poker")  # 'games' is first part here, not second
