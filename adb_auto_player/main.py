import adb_auto_player.logger as logging

import adb_auto_player.adb as adb
import adb_auto_player.update_manager as update_manager
import adb_auto_player.plugin_loader as plugin_loader
from adb_auto_player.logging_setup import update_logging_from_config, setup_logging

setup_logging()

if __name__ == "__main__":
    main_config = plugin_loader.get_main_config()

    update_logging_from_config(main_config)

    version = update_manager.get_version_from_pyproject()
    logging.info(f"Using Version: {version}")
    if update_manager.is_new_version_available():
        logging.info(
            "New Version available: "
            "https://github.com/yulesxoxo/AdbAutoPlayer/releases/latest"
        )

    device = adb.get_device(main_config)
    app = adb.get_currently_running_app(device)

    plugins = plugin_loader.load_plugin_configs()
    plugin_name = None

    for plugin in plugins:
        if plugin.get("package") == app:
            plugin_name = str(plugin.get("name"))
            break

    if plugin_name is None:
        logging.critical_and_exit(f"No config found for: {app}")

    config = plugin_loader.load_config(plugin_name)

    if config is None:
        logging.critical_and_exit(f"Could not load config for: {plugin_name}")

    module = plugin_loader.load_plugin_module(plugin_name)

    if not module:
        logging.critical_and_exit(f"Could not load module for: {plugin_name}")

    module.execute(device, config)
