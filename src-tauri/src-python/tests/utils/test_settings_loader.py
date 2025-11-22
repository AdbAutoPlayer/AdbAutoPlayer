"""Tests for SettingsLoader module."""

import tomllib
from pathlib import Path
from unittest.mock import mock_open, patch

from adb_auto_player.file_loader import SettingsLoader
from adb_auto_player.models.pydantic import (
    AdbSettings,
)


class TestSettingsLoader:
    """Test cases for SettingsLoader class."""

    def test_games_dir_first_candidate_exists(self):
        """Test games_dir when first candidate exists."""
        working_path = Path("home") / "user" / "project"

        with patch.object(SettingsLoader, "working_dir", return_value=working_path):
            with patch("pathlib.Path.exists") as mock_exists:
                # First candidate exists
                mock_exists.side_effect = lambda: True

                result = SettingsLoader.games_dir()
                expected = working_path / "games"
                assert result == expected

    def test_games_dir_fallback_to_default(self):
        """Test games_dir falls back to first candidate when none exist."""
        working_path = Path("home") / "user" / "project"

        with patch.object(SettingsLoader, "working_dir", return_value=working_path):
            with patch("pathlib.Path.exists", return_value=False):
                result = SettingsLoader.games_dir()
                expected = working_path / "games"  # First candidate
                assert result == expected

    def test_binaries_dir(self):
        """Test binaries_dir returns games_dir parent / binaries."""
        games_path = Path("home") / "user" / "project" / "games"
        expected = Path("home") / "user" / "project" / "binaries"

        with patch.object(SettingsLoader, "games_dir", return_value=games_path):
            result = SettingsLoader.binaries_dir()
            assert result == expected

    def test_adb_settings_real_data(self):
        settings = SettingsLoader.adb_settings()
        assert settings.advanced.hardware_decoding

    def test_adb_settings_successful_load(self):
        """Test successfully loads valid TOML file."""
        settings_data = {"device": {"ID": "test"}}
        working_path = Path("home") / "user" / "project"

        with patch.object(SettingsLoader, "working_dir", return_value=working_path):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", mock_open()):
                    with patch("tomllib.load", return_value=settings_data):
                        result = SettingsLoader.adb_settings()
                        assert result.device.id == "test"

    def test_adb_settings_file_not_found(self):
        """Test adb_settings handles file not found gracefully."""
        working_path = Path("home") / "user" / "project"

        with patch.object(SettingsLoader, "working_dir", return_value=working_path):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("builtins.open", side_effect=FileNotFoundError()):
                    result = SettingsLoader.adb_settings()
                    assert isinstance(result, AdbSettings)

    def test_adb_settings_toml_decode_error(self):
        """Test adb_settings handles TOML parsing errors gracefully."""
        working_path = Path("home") / "user" / "project"

        with patch.object(SettingsLoader, "working_dir", return_value=working_path):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", mock_open()):
                    with patch(
                        "tomllib.load",
                        side_effect=tomllib.TOMLDecodeError("Invalid TOML", "", 0),
                    ):
                        result = SettingsLoader.adb_settings()
                        assert isinstance(result, AdbSettings)

    def test_adb_settings_permission_error(self):
        """Test adb_settings handles permission errors gracefully."""
        working_path = Path("home") / "user" / "project"

        with patch.object(SettingsLoader, "working_dir", return_value=working_path):
            with patch("pathlib.Path.exists", return_value=True):
                with patch(
                    "builtins.open", side_effect=PermissionError("Permission denied")
                ):
                    result = SettingsLoader.adb_settings()
                    assert isinstance(result, AdbSettings)
