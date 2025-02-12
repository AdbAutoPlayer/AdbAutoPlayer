import tomllib
from pathlib import Path

from typing import Any

import logging

working_dir_path: Path | None = None
games_dir_path: Path | None = None


def __get_working_dir() -> Path:
    global working_dir_path
    if working_dir_path is not None:
        return working_dir_path
    else:
        working_dir_path = Path.cwd()
        logging.debug(f"Python working dir: {working_dir_path}")
        return working_dir_path


def get_games_dir() -> Path:
    global games_dir_path
    if games_dir_path is not None:
        return games_dir_path

    working_dir = __get_working_dir()

    # run main directly
    if "python" in working_dir.parts and "adb_auto_player" in working_dir.parts:
        games_dir_path = working_dir / "games"
    # dev
    if not games_dir_path or not games_dir_path.exists():
        games_dir_path = (
            working_dir.parent.parent / "python" / "adb_auto_player" / "games"
        )
    # prod
    if not games_dir_path.exists():
        games_dir_path = working_dir / "games"

    logging.debug(f"Python games dir: {games_dir_path}")
    return games_dir_path


def get_binaries_dir() -> Path:
    return get_games_dir().parent / "binaries"


def get_main_config() -> dict[str, Any]:
    working_dir = __get_working_dir()
    config_toml_path = None
    if "python" in working_dir.parts and "adb_auto_player" in working_dir.parts:
        config_toml_path = working_dir.parent.parent / "cmd" / "wails" / "config.toml"

    if not config_toml_path or not config_toml_path.exists():
        config_toml_path = working_dir / "config.toml"

    if not config_toml_path or not config_toml_path.exists():
        config_toml_path = working_dir.parent / "config.toml"

    logging.debug(f"Python config.toml path: {config_toml_path}")
    with open(config_toml_path, "rb") as f:
        return tomllib.load(f)
