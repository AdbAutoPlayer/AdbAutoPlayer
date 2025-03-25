"""ADB Auto Player Config Loader Module."""

import logging
import tomllib
from pathlib import Path
from typing import Any, Literal, Optional


class ConfigLoader:
    """Singleton class for lazily computing and caching configuration paths."""

    _instance: Optional["ConfigLoader"] = None
    _working_dir: Path
    _games_dir: Path | None
    # False = no config using default values
    _main_config: dict[str, Any] | None | Literal[False]

    def __new__(cls) -> "ConfigLoader":
        """New for Singleton."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize the ConfigLoader singleton."""
        self._working_dir = Path.cwd()
        self._games_dir = None
        self._main_config = None
        logging.debug(f"Python working dir path: {self._working_dir}")

    @property
    def working_dir(self) -> Path:
        """Return the current working directory."""
        return self._working_dir

    @property
    def games_dir(self) -> Path:
        """Determine and return the games directory."""
        if self._games_dir is None:
            candidates: list[Path] = [
                self.working_dir / "games",  # distributed GUI Context
                self.working_dir.parent / "games",  # distributed CLI Context
                self.working_dir / "adb_auto_player" / "games",
                self.working_dir.parent.parent / "python" / "adb_auto_player" / "games",
            ]
            self._games_dir = next((c for c in candidates if c.exists()), candidates[0])
            logging.debug(f"Python games path: {self._games_dir}")
        return self._games_dir

    @property
    def binaries_dir(self) -> Path:
        """Return the binaries directory."""
        return self.games_dir.parent / "binaries"

    @property
    def main_config(self) -> dict[str, Any]:
        """Locate and load the main config.toml file."""
        if isinstance(self._main_config, dict):
            return self._main_config

        if self._main_config is False:
            return {}

        candidates: list[Path] = [
            self.working_dir / "config.toml",  # distributed GUI context
            self.working_dir.parent / "config.toml",  # distributed CLI context
            self.working_dir.parent / "config" / "config.toml",  # Python CLI in /python
            self.working_dir.parent.parent / "config" / "config.toml",  # PyCharm
        ]

        config_toml_path: Path = next(
            (c for c in candidates if c.exists()), candidates[0]
        )
        logging.debug(f"Python config.toml path: {config_toml_path}")
        try:
            with open(config_toml_path, "rb") as f:
                main_config = tomllib.load(f)
            self._main_config = main_config
            return main_config
        except Exception as e:
            logging.debug(f"Failed to load main config: {e}")
            logging.info("Using default main config values")
            self._main_config = False
        return {}
