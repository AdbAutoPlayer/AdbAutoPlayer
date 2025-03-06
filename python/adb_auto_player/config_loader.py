"""ADB Auto Player Config Loader Module."""

import logging
import tomllib
from pathlib import Path
from typing import Any

working_dir_path: Path | None = None
games_dir_path: Path | None = None


class ConfigLoader:
    """Class for lazily computing and caching configuation paths."""

    def __init__(self) -> None:
        """Initialize ConfigLoader."""
        self._working_dir: Path = Path.cwd()

    @property
    def working_dir(self) -> Path:
        """Return the current working directory."""
        logging.debug(f"Python working dir: {working_dir_path}")
        return self._working_dir

    @property
    def games_dir(self) -> Path:
        """Determine and return the games directory."""
        candidate: Path = self.working_dir / "adb_auto_player" / "games"

        if candidate.exists():
            games: Path = candidate
        else:
            fallback: Path = (
                self.working_dir.parent.parent / "python" / "adb_auto_player" / "games"
            )
            games = fallback if fallback.exists() else candidate

        logging.debug(f"Python games dir: {games}")

        return games

    @property
    def binaries_dir(self) -> Path:
        """Return the binaries directory."""
        return self.games_dir.parent / "binaries"

    @property
    def main_config(self) -> dict[str, Any]:
        """Locate and load the main config.toml file."""
        config_toml_path: Path = None  # type: ignore

        if (
            "python" in self.working_dir.parts
            and "adb_auto_player" in self.working_dir.parts
        ):
            config_toml_path = (
                self.working_dir.parent.parent / "cmd" / "wails" / "config.toml"
            )

        if not config_toml_path or not config_toml_path.exists():
            config_toml_path = self.working_dir / "config.toml"

        if not config_toml_path or not config_toml_path.exists():
            config_toml_path = self.working_dir.parent / "config.toml"

        logging.debug(f"Python config.toml path: {config_toml_path}")
        with open(config_toml_path, "rb") as f:
            return tomllib.load(f)
