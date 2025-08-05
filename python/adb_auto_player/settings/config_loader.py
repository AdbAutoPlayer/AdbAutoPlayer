"""ADB Auto Player Config Loader Module."""

import logging
from functools import lru_cache
from pathlib import Path

from adb_auto_player.decorators import register_cache
from adb_auto_player.models.decorators import CacheGroup
from adb_auto_player.models.pydantic.general_settings import GeneralSettings


class ConfigLoader:
    """Utility class for resolving and caching important configuration paths."""

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
        working_dir = ConfigLoader.working_dir()
        candidates: list[Path] = [
            working_dir / "games",  # Windows distributed GUI Context
            working_dir.parent / "games",  # Windows distributed CLI Context
            working_dir / "adb_auto_player" / "games",  # dev
            working_dir.parent / "Resources" / "games",  # MacOS .app Bundle
        ]
        games_dir = next((c for c in candidates if c.exists()), candidates[0])
        logging.debug(f"Python games path: {games_dir}")
        return games_dir

    @staticmethod
    @lru_cache(maxsize=1)
    def binaries_dir() -> Path:
        """Return the binaries directory."""
        return ConfigLoader.games_dir().parent / "binaries"

    @staticmethod
    @register_cache(CacheGroup.GENERAL_SETTINGS)
    @lru_cache(maxsize=1)
    def general_settings() -> GeneralSettings:
        """Locate and load the general settings config.toml file."""
        working_dir = ConfigLoader.working_dir()
        candidates: list[Path] = [
            working_dir / "config.toml",  # distributed GUI context
            working_dir.parent / "config.toml",  # distributed CLI context
            working_dir.parent / "config" / "config.toml",  # Python CLI in /python
            working_dir.parent.parent / "config" / "config.toml",  # PyCharm
        ]

        config_toml_path: Path = next(
            (c for c in candidates if c.exists()), candidates[0]
        )
        logging.debug(f"Python config.toml path: {config_toml_path}")
        return GeneralSettings.from_toml(config_toml_path)
