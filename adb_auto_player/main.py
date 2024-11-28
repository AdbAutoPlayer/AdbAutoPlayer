import logging

import adb_auto_player.adb as adb
import adb_auto_player.plugin_loader as plugin_loader
from adb_auto_player.logging_setup import update_logging_from_config, setup_logging

setup_logging()

if __name__ == "__main__":
    main_config = plugin_loader.get_main_config()

    update_logging_from_config(main_config)

    device = adb.get_device(main_config)
    app = adb.get_currently_running_app(device)

    if not app:
        raise SystemError

    plugins = plugin_loader.load_plugin_configs()
    plugin_name = None

    for plugin in plugins:
        if plugin.get("package") == app:
            plugin_name = str(plugin.get("name"))
            break

    if plugin_name is None:
        logging.critical(f"No config found for: {app}")

    config = plugin_loader.load_config(plugin_name)  # type: ignore

    if config is None:
        logging.critical(f"Could not load config for: {plugin_name}")

    module = plugin_loader.load_plugin_module(plugin_name)  # type: ignore

    if not module:
        logging.critical(f"Could not load module for: {plugin_name}")

    module.execute(device, config)
