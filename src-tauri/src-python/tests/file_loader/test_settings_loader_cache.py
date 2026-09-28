"""Tests for `SettingsLoader` cache invalidation.

Regression test for: `adb_settings()` / `app_settings()` registered an inner,
uncached loader in `CACHE_REGISTRY` instead of their cached wrapper. Clearing
the `ADB_SETTINGS` / `APP_SETTINGS` group after saving the settings was a no-op,
so the settings form (and anything else in the main process) kept showing the
old values, e.g. a toggled option reappearing as off, until the app restarted.
"""

from pathlib import Path

import pytest
from adb_auto_player.file_loader import SettingsLoader
from adb_auto_player.models.decorators import CacheGroup
from adb_auto_player.registries import CACHE_REGISTRY
from adb_auto_player.tauri_context.context import TauriContext

_PROFILE_INDEX = 0


def _cache_clear(group: CacheGroup) -> None:
    """Mirror `__main__._cache_clear`, which can't be imported without pytauri."""
    for func, profile_aware in CACHE_REGISTRY.get(group, []):
        if cache_clear_func := getattr(func, "cache_clear", None):
            if profile_aware:
                cache_clear_func(_PROFILE_INDEX)
            else:
                cache_clear_func()


@pytest.fixture
def config_dir(tmp_path: Path):
    TauriContext.set_profile_index(_PROFILE_INDEX)
    SettingsLoader.set_app_config_dir(tmp_path)
    SettingsLoader.adb_settings.cache_clear()
    SettingsLoader.app_settings.cache_clear()
    yield tmp_path
    SettingsLoader.adb_settings.cache_clear()
    SettingsLoader.app_settings.cache_clear()
    TauriContext.set_profile_index(None)


class TestSettingsCacheClear:
    def test_adb_settings_reloaded_after_group_clear(self, config_dir: Path):
        settings_file = config_dir / "ADB.toml"
        settings_file.write_text("[wireless_debugging]\nenabled = false\n")
        assert not SettingsLoader.adb_settings().wireless_debugging.enabled

        settings_file.write_text("[wireless_debugging]\nenabled = true\n")
        _cache_clear(CacheGroup.ADB_SETTINGS)

        assert SettingsLoader.adb_settings().wireless_debugging.enabled

    def test_app_settings_reloaded_after_group_clear(self, config_dir: Path):
        settings_file = config_dir / "AdbAutoPlayer.toml"
        settings_file.write_text('[logging]\nlevel = "INFO"\n')
        assert SettingsLoader.app_settings().logging.level == "INFO"

        settings_file.write_text('[logging]\nlevel = "DEBUG"\n')
        _cache_clear(CacheGroup.APP_SETTINGS)

        assert SettingsLoader.app_settings().logging.level == "DEBUG"

    def test_adb_settings_still_cached_without_clear(self, config_dir: Path):
        settings_file = config_dir / "ADB.toml"
        settings_file.write_text('[device]\nid = "first:1"\n')
        first = SettingsLoader.adb_settings()

        settings_file.write_text('[device]\nid = "second:2"\n')

        assert SettingsLoader.adb_settings() is first
