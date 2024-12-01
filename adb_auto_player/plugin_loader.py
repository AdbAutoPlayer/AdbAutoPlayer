import hashlib
import importlib.util
import json
import os
import sys
import tomllib
import types
from typing import Any, cast, NoReturn

import adb_auto_player.logger as logging

PLUGIN_LIST_FILE = "plugin_list.json"
PLUGIN_CONFIG_FILE = "config.toml"
MAIN_CONFIG_FILE = "main_config.toml"


def get_plugins_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "plugins")
    return os.path.join("plugins")


def get_main_config() -> dict[str, Any]:
    if getattr(sys, "frozen", False):
        config_file = os.path.join(os.path.dirname(sys.executable), MAIN_CONFIG_FILE)
    else:
        config_file = os.path.join(MAIN_CONFIG_FILE)
    with open(config_file, "rb") as f:
        return tomllib.load(f)


def scan_plugins() -> list[dict[str, Any]]:
    plugins = []

    for plugin_dir in os.listdir(get_plugins_dir()):
        config = load_config(plugin_dir)

        if config:
            plugin_config = config.get("plugin", {})
            package = plugin_config.get("package")
            name = plugin_config.get("name")
            plugin = {
                "package": package,
                "name": name,
                "dir": plugin_dir,
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


def load_plugin_configs() -> list[dict[str, Any]]:
    if os.path.exists(PLUGIN_LIST_FILE):
        with open(PLUGIN_LIST_FILE, "r") as f:
            cached_plugins = json.load(f)

        if cached_plugins.get("hash") == generate_plugin_list_hash():
            return cast(list[dict[str, Any]], cached_plugins["plugins"])

    plugins = scan_plugins()
    create_plugin_list_file(plugins)

    return plugins


def create_plugin_list_file(plugins: list[dict[str, Any]]) -> None:
    plugin_data = {"hash": generate_plugin_list_hash(), "plugins": plugins}

    with open(PLUGIN_LIST_FILE, "w") as f:
        json.dump(plugin_data, f, indent=4)


def load_config(plugin_name: str) -> dict[str, Any]:
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


def get_plugin_for_app(
    plugins: list[dict[str, Any]], app: str
) -> dict[str, Any] | None:
    for plugin in plugins:
        if plugin.get("package") == app:
            return plugin
    return None
