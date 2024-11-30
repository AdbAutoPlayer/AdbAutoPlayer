import shutil
import os
import sys
import zipfile
from io import BytesIO
from typing import Any, Dict

import requests
import tomllib
import adb_auto_player.logger as logging
from pathlib import Path
from packaging.version import Version

GITHUB_REPO: str = "yulesxoxo/AdbAutoPlayer"
RELEASE_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
PYPROJECT_VERSION: str | None = None
LATEST_RELEASE_JSON: Dict[str, Any] | None = None


def get_version_from_pyproject() -> str:
    global PYPROJECT_VERSION
    if PYPROJECT_VERSION is not None:
        return PYPROJECT_VERSION

    if getattr(sys, "frozen", False):
        pyproject_toml_path = os.path.join(
            sys._MEIPASS,  # type: ignore
            "pyproject.toml",
        )
    else:
        pyproject_toml_path = os.path.join(Path(os.getcwd()).parent, "pyproject.toml")

    with open(pyproject_toml_path, "rb") as f:
        pyproject_toml_file = tomllib.load(f)

    PYPROJECT_VERSION = str(pyproject_toml_file["tool"]["poetry"]["version"])
    return PYPROJECT_VERSION


def __get_latest_release_json() -> Dict[str, Any] | None:
    global LATEST_RELEASE_JSON
    if LATEST_RELEASE_JSON is not None:
        return LATEST_RELEASE_JSON

    response = requests.get(RELEASE_API_URL)
    if response.status_code != 200:
        return None

    LATEST_RELEASE_JSON = response.json()
    return LATEST_RELEASE_JSON


def __get_latest_version() -> str | None:
    json = __get_latest_release_json()
    if json is None:
        logging.error("Could not fetch the latest release")
        return None

    return str(json["tag_name"])


def __get_browser_download_url() -> str | None:
    release_json = __get_latest_release_json()
    if release_json is None:
        logging.error("Could not fetch the latest release")
        return None

    for asset in release_json.get("assets", []):
        if asset["name"] == "plugins.zip":
            return str(asset["browser_download_url"])

    return None


def __get_version_from_version_check_file() -> str | None:
    version_check_path = Path("VERSION_CHECK")
    if version_check_path.exists():
        with version_check_path.open() as f:
            return f.read().strip()

    return None


def __get_last_checked_version() -> str:
    version_check = __get_version_from_version_check_file()
    pyproject_version = get_version_from_pyproject()
    if version_check is None:
        return pyproject_version
    if Version(version_check) > Version(pyproject_version):
        return version_check
    return pyproject_version


def __is_new_version_available() -> bool:
    last_checked_version = __get_last_checked_version()
    latest_version = __get_latest_version()
    if latest_version is None:
        return False

    return Version(last_checked_version) < Version(latest_version)


def __download_and_extract_plugins(url: str) -> bool:
    response = requests.get(url)
    if response.status_code != 200:
        logging.error("Could not fetch the latest release")
        return False
    with zipfile.ZipFile(BytesIO(response.content)) as zip_ref:
        zip_ref.extractall("./tmp")
        return True


def __install_compatible_plugins() -> bool | None:
    base_dir = "tmp/plugins/"
    if not os.path.exists(base_dir):
        logging.debug(f"The directory {base_dir} does not exist.")
        return None

    all_plugins_installed: bool = True
    for dir_name in os.listdir(base_dir):
        dir_path = os.path.join(base_dir, dir_name)

        config_path = os.path.join(dir_path, "config.toml")
        if os.path.exists(config_path):
            try:
                with open(config_path, "rb") as f:
                    config_data = tomllib.load(f)
            except Exception as e:
                logging.debug(f"Exception in install_compatible_plugins: {e}")
                continue
        else:
            logging.debug(f"Config missing: {config_path}")
            continue

        if config_data is None:
            continue

        min_adb_auto_player_version: str | None = config_data.get("plugin", {}).get(
            "min_adb_auto_player_version", None
        )
        if min_adb_auto_player_version is None:
            continue
        if Version(min_adb_auto_player_version) <= Version(
            get_version_from_pyproject()
        ):
            __install_plugin_from_tmp(dir_path, dir_name)
        else:
            all_plugins_installed = False

    return all_plugins_installed


def __install_plugin_from_tmp(dir_path: str, dir_name: str) -> None:
    plugin_dir = f"./plugins/{dir_name}"
    os.makedirs(plugin_dir, exist_ok=True)
    for item in os.listdir(dir_path):
        source_item = os.path.join(dir_path, item)
        dest_item = os.path.join(plugin_dir, item)
        if os.path.isdir(source_item):
            shutil.copytree(source_item, dest_item, dirs_exist_ok=True)
        else:
            shutil.copy2(source_item, dest_item)
    logging.info(f"Plugin updated: {dir_name}")


def update_plugins() -> None | bool:
    if not __is_new_version_available():
        return None

    latest_version = __get_latest_version()
    browser_download_url = __get_browser_download_url()
    if latest_version is None or browser_download_url is None:
        return None

    if not __download_and_extract_plugins(browser_download_url):
        return None

    with open("VERSION_CHECK", "w") as version_file:
        version_file.write(latest_version)
    all_plugins_installed = __install_compatible_plugins()
    shutil.rmtree("./tmp")
    return all_plugins_installed
