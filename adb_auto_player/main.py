import adb_auto_player.logger as logging

import adb_auto_player.adb as adb
import adb_auto_player.update_manager as update_manager
import adb_auto_player.plugin_loader as plugin_loader
from adb_auto_player.logging_setup import update_logging_from_config, setup_logging

setup_logging()

if __name__ == "__main__":
    main_config = plugin_loader.get_main_config()
    update_logging_from_config(main_config)
    update_manager.version_updater()

    device = adb.get_device(main_config)
    app = adb.get_currently_running_app(device)

    plugin = plugin_loader.get_plugin_for_app(
        plugin_loader.load_plugin_configs(),
        app,
    )
    if plugin is None:
        logging.critical_and_exit(f"No config found for: {app}")

    plugin_dir = str(plugin.get("dir"))
    config = plugin_loader.load_config(plugin_dir)

    if config is None:
        logging.critical_and_exit(f"Could not load config for: {plugin_dir}")

    module = plugin_loader.load_plugin_module(plugin_dir)

    if not module:
        logging.critical_and_exit(f"Could not load module for: {plugin_dir}")

    module.execute(device, config)
