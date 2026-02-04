"""Tests for SettingsLoader module."""

import unittest
from pathlib import Path

from adb_auto_player.file_loader import SettingsLoader


class TestSettingsLoader(unittest.TestCase):
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
        self.assertFalse(settings.advanced.hardware_decoding)


if __name__ == "__main__":
    unittest.main()
