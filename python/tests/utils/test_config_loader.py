"""Tests for ConfigLoader module."""

import tempfile
import tomllib
from pathlib import Path
from unittest.mock import mock_open, patch

from adb_auto_player.util import ConfigLoader


class TestConfigLoader:
    """Test cases for ConfigLoader class."""

    def setup_method(self):
        """Clear the LRU cache before each test."""
        ConfigLoader.working_dir.cache_clear()
        ConfigLoader.games_dir.cache_clear()
        ConfigLoader.binaries_dir.cache_clear()
        ConfigLoader.main_config.cache_clear()

    def test_working_dir_normal_case(self):
        """Test working_dir returns current working directory in normal case."""
        mock_cwd_path = Path("home") / "user" / "project"

        with patch("pathlib.Path.cwd", return_value=mock_cwd_path):
            result = ConfigLoader.working_dir()
            assert result == mock_cwd_path

    def test_working_dir_from_tests_directory(self):
        """Test working_dir fallback when run from tests directory."""
        mock_cwd_path = Path("home") / "user" / "python" / "tests" / "unit"
        expected_path = Path("home") / "user" / "python"

        with patch("pathlib.Path.cwd", return_value=mock_cwd_path):
            result = ConfigLoader.working_dir()
            assert result == expected_path

    def test_working_dir_python_tests_not_consecutive(self):
        """Test working_dir when python and tests are not consecutive."""
        mock_cwd_path = Path("home") / "user" / "python" / "src" / "tests"

        with patch("pathlib.Path.cwd", return_value=mock_cwd_path):
            result = ConfigLoader.working_dir()
            # Should return original path since tests doesn't immediately follow python
            assert result == mock_cwd_path

    def test_working_dir_no_python_in_path(self):
        """Test working_dir when 'python' is not in path."""
        mock_cwd_path = Path("home") / "user" / "project" / "tests"

        with patch("pathlib.Path.cwd", return_value=mock_cwd_path):
            result = ConfigLoader.working_dir()
            assert result == mock_cwd_path

    def test_working_dir_no_tests_in_path(self):
        """Test working_dir when 'tests' is not in path."""
        mock_cwd_path = Path("home") / "user" / "python" / "src"

        with patch("pathlib.Path.cwd", return_value=mock_cwd_path):
            result = ConfigLoader.working_dir()
            assert result == mock_cwd_path

    def test_games_dir_first_candidate_exists(self):
        """Test games_dir when first candidate exists."""
        working_path = Path("home") / "user" / "project"

        with patch.object(ConfigLoader, "working_dir", return_value=working_path):
            with patch("pathlib.Path.exists") as mock_exists:
                # First candidate exists
                mock_exists.side_effect = lambda: True

                result = ConfigLoader.games_dir()
                expected = working_path / "games"
                assert result == expected

    def test_games_dir_fallback_to_default(self):
        """Test games_dir falls back to first candidate when none exist."""
        working_path = Path("home") / "user" / "project"

        with patch.object(ConfigLoader, "working_dir", return_value=working_path):
            with patch("pathlib.Path.exists", return_value=False):
                result = ConfigLoader.games_dir()
                expected = working_path / "games"  # First candidate
                assert result == expected

    def test_binaries_dir(self):
        """Test binaries_dir returns games_dir parent / binaries."""
        games_path = Path("home") / "user" / "project" / "games"
        expected = Path("home") / "user" / "project" / "binaries"

        with patch.object(ConfigLoader, "games_dir", return_value=games_path):
            result = ConfigLoader.binaries_dir()
            assert result == expected

    def test_main_config_successful_load(self):
        """Test main_config successfully loads valid TOML file."""
        config_data = {"app": {"name": "test"}}
        working_path = Path("home") / "user" / "project"

        with patch.object(ConfigLoader, "working_dir", return_value=working_path):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", mock_open()):
                    with patch("tomllib.load", return_value=config_data):
                        result = ConfigLoader.main_config()
                        assert result == config_data

    def test_main_config_file_not_found(self):
        """Test main_config handles file not found gracefully."""
        working_path = Path("home") / "user" / "project"

        with patch.object(ConfigLoader, "working_dir", return_value=working_path):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("builtins.open", side_effect=FileNotFoundError()):
                    result = ConfigLoader.main_config()
                    assert result == {}

    def test_main_config_toml_decode_error(self):
        """Test main_config handles TOML parsing errors gracefully."""
        working_path = Path("home") / "user" / "project"

        with patch.object(ConfigLoader, "working_dir", return_value=working_path):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("builtins.open", mock_open()):
                    with patch(
                        "tomllib.load",
                        side_effect=tomllib.TOMLDecodeError("Invalid TOML", "", 0),
                    ):
                        result = ConfigLoader.main_config()
                        assert result == {}

    def test_main_config_permission_error(self):
        """Test main_config handles permission errors gracefully."""
        working_path = Path("home") / "user" / "project"

        with patch.object(ConfigLoader, "working_dir", return_value=working_path):
            with patch("pathlib.Path.exists", return_value=True):
                with patch(
                    "builtins.open", side_effect=PermissionError("Permission denied")
                ):
                    result = ConfigLoader.main_config()
                    assert result == {}

    def test_integration_with_real_temp_directories(self):
        """Integration test using real temporary directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a python/tests structure
            python_dir = temp_path / "python"
            tests_dir = python_dir / "tests"
            tests_dir.mkdir(parents=True)

            with patch("pathlib.Path.cwd", return_value=tests_dir):
                ConfigLoader.working_dir.cache_clear()
                result = ConfigLoader.working_dir()
                assert result == python_dir
