import os
import sys
import requests
import tomllib
import adb_auto_player.logger as logging
from pathlib import Path
from packaging.version import Version

REPO_OWNER: str = "yulesxoxo"
REPO_NAME: str = "AdbAutoPlayer"


def get_version_from_pyproject() -> str:
    if getattr(sys, "frozen", False):
        pyproject_toml_path = os.path.join(
            sys._MEIPASS,  # type: ignore
            "pyproject.toml",
        )
    else:
        pyproject_toml_path = os.path.join(Path(os.getcwd()).parent, "pyproject.toml")

    with open(pyproject_toml_path, "rb") as f:
        pyproject_toml_file = tomllib.load(f)

    return str(pyproject_toml_file["tool"]["poetry"]["version"])


def get_latest_version() -> str | None:
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
    response = requests.get(url)
    if response.status_code == 200:
        return str(response.json()["tag_name"])
    else:
        logging.error("Could not fetch the latest release information")
        return None


def is_new_version_available() -> bool:
    pyproject_version = get_version_from_pyproject()
    # return false for local dev
    if pyproject_version == "0.0.0":
        return False

    latest_version = get_latest_version()
    if latest_version is None:
        return False

    return Version(pyproject_version) < Version(latest_version)
