"""ADB Auto Player Settings Loader Module."""

import contextvars
import logging
from pathlib import Path

from adb_auto_player.decorators import register_cache
from adb_auto_player.models.decorators import CacheGroup
from adb_auto_player.models.pydantic import (
    AdbSettings,
)
from adb_auto_player.tauri_context import profile_aware_cache

_profile_app_config_dir: contextvars.ContextVar[Path | None] = contextvars.ContextVar(
    "profile_app_config_dir", default=None
)
_profile_resource_dir: contextvars.ContextVar[Path | None] = contextvars.ContextVar(
    "profile_resource_dir", default=None
)


class SettingsLoader:
    """Utility class for resolving and caching important settings paths."""

    @staticmethod
    def get_app_config_dir() -> Path:
        """Get App Config Dir."""
        value = _profile_app_config_dir.get()
        if value is None:
            raise RuntimeError("App Config Dir undefined")
        return value

    @staticmethod
    def set_app_config_dir(value: Path) -> None:
        """Set App Config Dir."""
        _profile_app_config_dir.set(value)

    @staticmethod
    def get_resource_dir() -> Path:
        """Get resource dir."""
        value = _profile_resource_dir.get()
        if value is None:
            raise RuntimeError("Resource Dir undefined")
        return value

    @staticmethod
    def set_resource_dir(value: Path) -> None:
        """Set resource dir.

        Expects contents to have the structure as the adb_auto_player project dir.
        ./games/afk_journey/templates/...
        ./binaries/...
        """
        _profile_resource_dir.set(value)

    @staticmethod
    def games_dir() -> Path:
        """Determine and return the games directory."""
        return SettingsLoader.get_resource_dir() / "games"

    @staticmethod
    def binaries_dir() -> Path:
        """Return the binaries directory."""
        return SettingsLoader.get_resource_dir() / "binaries"

    @staticmethod
    def settings_dir() -> Path:
        """Return the settings directory."""
        return SettingsLoader.get_app_config_dir()

    @staticmethod
    @register_cache(CacheGroup.ADB_SETTINGS)
    @profile_aware_cache(maxsize=1)
    def adb_settings() -> AdbSettings:
        """Locate and load the general settings AdbAutoPlayer.toml file."""
        settings_file_path = SettingsLoader.settings_dir() / "ADB.toml"
        logging.debug(f"Python AdbAutoPlayer.toml path: {settings_file_path}")
        return AdbSettings.from_toml(settings_file_path)
