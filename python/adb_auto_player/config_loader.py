"""ADB Auto Player Config Loader Module."""

import logging
import tomllib
from pathlib import Path
from typing import Any


class ConfigLoader:
    """Class for lazily computing and caching configuation paths."""

    def __init__(self) -> None:
        """Initialize ConfigLoader."""
        self._working_dir: Path = Path.cwd()
        logging.debug(f"Python working dir: {self._working_dir}")

    @property
    def working_dir(self) -> Path:
        """Return the current working directory."""
        return self._working_dir

    @property
    def games_dir(self) -> Path:
        """Determine and return the games directory."""
        candidates: list[Path] = [
            self.working_dir / "games",  # distributed GUI Context
            self.working_dir.parent / "games",  # distributed CLI Context
            self.working_dir / "adb_auto_player" / "games",
            self.working_dir.parent.parent / "python" / "adb_auto_player" / "games",
        ]
        games: Path = next((c for c in candidates if c.exists()), candidates[0])

        logging.debug(f"Python games dir: {games}")
        return games

    @property
    def binaries_dir(self) -> Path:
        """Return the binaries directory."""
        return self.games_dir.parent / "binaries"

    @property
    def main_config(self) -> dict[str, Any]:
        """Locate and load the main config.toml file."""
        candidates: list[Path] = [
            self.working_dir / "config.toml",  # distributed GUI context
            self.working_dir.parent / "config.toml",  # distributed CLI context
            self.working_dir.parent / "config" / "config.toml",  # Python CLI in /python
            self.working_dir.parent.parent / "config" / "config.toml",  # PyCharm
        ]

        # Find the first existing candidate or default to the first path
        config_toml_path: Path = next(
            (c for c in candidates if c.exists()), candidates[0]
        )

        logging.debug(f"Python config.toml path: {config_toml_path}")
        with open(config_toml_path, "rb") as f:
            return tomllib.load(f)
