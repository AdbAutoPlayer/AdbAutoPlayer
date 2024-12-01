import adb_auto_player.logger as logging

import adb_auto_player.adb as adb
import adb_auto_player.update_manager as update_manager
import adb_auto_player.plugin_loader as plugin_loader
from adb_auto_player.logging_setup import update_logging_from_config, setup_logging

setup_logging()


def __setup() -> None:
    update_logging_from_config(main_config)


def __version_updater() -> None:
    version = update_manager.get_version_from_pyproject()
    if version == "0.0.0":
        logging.info("Skipping updater for dev")
        return
    logging.info(f"Using Version: {version}")
    logging.info("Checking for updates")
    result = update_manager.update_plugins()
    if result is None:
        logging.info("No new updates")
    elif result is not None and not result:
        logging.warning(
            ".exe or binary needs to be updated: "
            "https://github.com/yulesxoxo/AdbAutoPlayer/releases/latest"
        )
    else:
        logging.info("Plugins updated successfully")
        logging.warning("Your plugin configs have been reset")


if __name__ == "__main__":
    main_config = plugin_loader.get_main_config()

    __setup()
    __version_updater()

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
