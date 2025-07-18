import logging
import os
import shutil
import sys
from functools import lru_cache
from pathlib import Path

import adbutils
from adb_auto_player.decorators import register_cache
from adb_auto_player.models.decorators import CacheGroup
from adb_auto_player.settings import ConfigLoader


@register_cache(CacheGroup.ADB)
@lru_cache(maxsize=1)
def _set_adb_path() -> None:
    """Helper function to set environment variable ADBUTILS_ADB_PATH depending on OS.

    Raises:
        FileNotFoundError: ADB executable not found in PATH.
    """
    is_frozen: bool = hasattr(sys, "frozen") or "__compiled__" in globals()

    if is_frozen and os.name == "nt":
        adb_env_path: str | None = os.getenv("ADBUTILS_ADB_PATH")

        if not adb_env_path or not os.path.isfile(adb_env_path):
            candidates: list[Path] = [
                ConfigLoader.binaries_dir() / "adb.exe",
                ConfigLoader.binaries_dir() / "windows" / "adb.exe",
            ]
            adb_env_path = str(
                next((c for c in candidates if c.exists()), candidates[0])
            )

        os.environ["ADBUTILS_ADB_PATH"] = adb_env_path

    if os.name != "nt":
        logging.debug(f"OS: {os.name}")
        path = os.getenv("PATH")
        paths = [
            "/opt/homebrew/bin",
            "/opt/homebrew/sbin",
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
            "/usr/sbin",
            "/sbin",
        ]

        path_dirs = []
        if path is not None:
            path_dirs = path.split(os.pathsep)
        for p in paths:
            if p not in path_dirs:
                path_dirs.append(p)

        path = os.pathsep.join(path_dirs)
        os.environ["PATH"] = path
        logging.debug(f"PATH: {path}")
        adb_path = shutil.which("adb")
        if not adb_path:
            raise FileNotFoundError("adb not found in system PATH")
        os.environ["ADBUTILS_ADB_PATH"] = adb_path

    logging.debug(f"ADBUTILS_ADB_PATH: {adbutils._utils.adb_path()}")
