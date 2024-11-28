import adb_auto_player.logger as logging
import os
import tomllib
import json
from typing import List, Dict, Any, cast, NoReturn
import hashlib
import importlib.util
import sys
import types

PLUGIN_LIST_FILE = "plugin_list.json"
PLUGIN_CONFIG_FILE = "config.toml"
MAIN_CONFIG_FILE = "main_config.toml"


def get_plugins_dir() -> str:
    return os.path.join("plugins")


def get_main_config() -> Dict[str, Any]:
    config_file = os.path.join(MAIN_CONFIG_FILE)
    with open(config_file, "rb") as f:
        return tomllib.load(f)


def scan_plugins() -> List[Dict[str, Any]]:
    plugins = []

    for plugin_name in os.listdir(get_plugins_dir()):
        config = load_config(plugin_name)

        if config:
            plugin_config = config.get("plugin", {})
            package = plugin_config.get("package")
            plugin = {
                "package": package,
                "name": plugin_name,
            }
            plugins.append(plugin)

    return plugins


def generate_plugin_list_hash() -> str:
    hash_md5 = hashlib.md5()

    plugins_dir = get_plugins_dir()

    for plugin_name in os.listdir(plugins_dir):
        plugin_dir = os.path.join(plugins_dir, plugin_name)
        config_file = os.path.join(plugin_dir, PLUGIN_CONFIG_FILE)

        if os.path.isdir(plugin_dir) and os.path.isfile(config_file):
            hash_md5.update(plugin_name.encode("utf-8"))
            hash_md5.update(str(os.path.getmtime(config_file)).encode("utf-8"))

    return hash_md5.hexdigest()


def load_plugin_configs() -> List[Dict[str, Any]]:
    if os.path.exists(PLUGIN_LIST_FILE):
        with open(PLUGIN_LIST_FILE, "r") as f:
            cached_plugins = json.load(f)

        if cached_plugins.get("hash") == generate_plugin_list_hash():
            return cast(List[Dict[str, Any]], cached_plugins["plugins"])

    plugins = scan_plugins()
    create_plugin_list_file(plugins)

    return plugins


def create_plugin_list_file(plugins: List[Dict[str, Any]]) -> None:
    plugin_data = {"hash": generate_plugin_list_hash(), "plugins": plugins}

    with open(PLUGIN_LIST_FILE, "w") as f:
        json.dump(plugin_data, f, indent=4)


def load_config(plugin_name: str) -> Dict[str, Any]:
    config_file = os.path.join(get_plugins_dir(), plugin_name, PLUGIN_CONFIG_FILE)
    with open(config_file, "rb") as f:
        return tomllib.load(f)


def load_plugin_module(plugin_name: str) -> types.ModuleType | NoReturn:
    plugin_main_path = os.path.join(get_plugins_dir(), plugin_name, "run.py")
    logging.debug(f"Loading plugin module: {plugin_main_path}")

    try:
        spec = importlib.util.spec_from_file_location(plugin_name, plugin_main_path)
        if spec is None:
            raise ValueError("Failed to load module spec")

        module = importlib.util.module_from_spec(spec)

        sys.modules[plugin_name] = module

        loader = spec.loader
        if loader is None:
            raise ValueError("Failed to load spec loader")

        loader.exec_module(module)

        return module
    except Exception as e:
        logging.critical_and_exit(f"Error loading plugin {plugin_name}: {e}")
