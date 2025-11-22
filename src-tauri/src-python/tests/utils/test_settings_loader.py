"""Tests for SettingsLoader module."""

from pathlib import Path

from adb_auto_player.file_loader import SettingsLoader


class TestSettingsLoader:
    """Test cases for SettingsLoader class."""

    def setUp(self):
        """Set up test fixtures."""
        src_tauri_dir = Path(__file__)
        for parent in src_tauri_dir.parents:
            if parent.name == "src-tauri":
                src_tauri_dir = parent
                break

        SettingsLoader.set_app_config_dir(src_tauri_dir / "Settings")

    def test_adb_settings_real_data(self):
        settings = SettingsLoader.adb_settings()
        assert not settings.advanced.hardware_decoding
