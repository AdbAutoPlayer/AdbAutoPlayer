"""ADB Auto Player Settings Loader Module."""

import logging
from functools import lru_cache
from pathlib import Path

from adb_auto_player.decorators import register_cache
from adb_auto_player.models.decorators import CacheGroup
from adb_auto_player.models.pydantic.adb_auto_player_settings import (
    AdbAutoPlayerSettings,
)


class SettingsLoader:
    """Utility class for resolving and caching important settings paths."""

    @staticmethod
    @lru_cache(maxsize=1)
    def working_dir() -> Path:
        """Return the current working directory."""
        working_dir = Path.cwd()
        try:
            parts = working_dir.parts
            if "python" in parts and "tests" in parts:
                python_index = parts.index("python")
                tests_index = parts.index("tests")
                if tests_index == python_index + 1:
                    # Rebuild the path up to 'python'
                    return Path(*parts[: python_index + 1])
        except ValueError:
            pass
        return working_dir

    @staticmethod
    @lru_cache(maxsize=1)
    def games_dir() -> Path:
        """Determine and return the games directory."""
        working_dir = SettingsLoader.working_dir()
        candidates: list[Path] = [
            working_dir / "games",  # Windows GUI .exe, PyCharm
            working_dir.parent / "games",  # Windows CLI .exe
            working_dir / "adb_auto_player" / "games",  # uv
            working_dir.parent / "Resources" / "games",  # MacOS .app Bundle
        ]
        games_dir = next((c for c in candidates if c.exists()), candidates[0])
        logging.debug(f"Python games path: {games_dir}")
        return games_dir

    @staticmethod
    @lru_cache(maxsize=1)
    def binaries_dir() -> Path:
        """Return the binaries directory."""
        return SettingsLoader.games_dir().parent / "binaries"

    @staticmethod
    @register_cache(CacheGroup.ADB_AUTO_PLAYER_SETTINGS)
    @lru_cache(maxsize=1)
    def adb_auto_player_settings() -> AdbAutoPlayerSettings:
        """Locate and load the general settings AdbAutoPlayer.toml file."""
        working_dir = SettingsLoader.working_dir()

        toml_rel_path = Path("settings") / "AdbAutoPlayer.toml"

        candidates: list[Path] = [
            working_dir / toml_rel_path,  #  Windows GUI .exe, macOS .app Bundle
            working_dir.parent / toml_rel_path,  # Windows CLI .exe, uv
            working_dir.parent.parent / toml_rel_path,  # PyCharm run config
        ]

        adb_auto_player_toml_path: Path = next(
            (c for c in candidates if c.exists()), candidates[0]
        )
        logging.debug(f"Python AdbAutoPlayer.toml path: {adb_auto_player_toml_path}")
        return AdbAutoPlayerSettings.from_toml(adb_auto_player_toml_path)
