"""Debug Commands."""

import logging
import pprint
import time

from adb_auto_player import ConfigLoader
from adb_auto_player.adb import (
    exec_wm_size,
    get_adb_client,
    get_adb_device,
    get_display_info,
    get_running_app,
    log_devices,
    wm_size_reset,
)
from adb_auto_player.commands.gui_categories import CommandCategory
from adb_auto_player.decorators.register_command import GuiMetadata, register_command


@register_command(
    gui=GuiMetadata(
        label="Log Debug Info",
        category=CommandCategory.SETTINGS_PHONE_DEBUG,
    ),
    name="Debug",
)
def _log_debug() -> None:
    logging.info("--- Debug Info Start ---")
    logging.info("--- Main Config ---")
    config = ConfigLoader().main_config
    logging.info(f"Config: {pprint.pformat(config)}")
    logging.info("--- ADB Client ---")
    client = None
    try:
        client = get_adb_client()
        log_devices(client.list(), logging.INFO)
    except Exception as e:
        logging.error(f"Error: {e}")

    device = None
    if client:
        logging.info("--- ADB Device ---")
        try:
            device = get_adb_device(adb_client=client)
        except Exception as e:
            logging.error(f"Error: {e}")

    if device:
        logging.info("--- Device Info ---")
        logging.info(f"Device Serial: {device.serial}")
        logging.info(f"Device Info: {device.info}")
        _ = get_running_app(device)

        logging.info("--- Testing Input Delay ---")
        total_time: float = 0.0
        iterations = 10

        for i in range(iterations):
            start_time = time.time()
            device.click(-1, -1)
            end_time = time.time()

            elapsed_time = (end_time - start_time) * 1000  # convert to milliseconds
            total_time += elapsed_time

        average_time = total_time / iterations
        logging.info(
            "Average time taken to tap screen "
            f"{iterations} times: {average_time:.2f} ms"
        )

        logging.info("--- Device Display ---")
        display_info = get_display_info(device)
        logging.info(f"Resolution: {display_info.width}x{display_info.height}")
        logging.info(f"Orientation: {display_info.orientation}")
        logging.info("--- Test Resize Display ---")
        try:
            exec_wm_size("1080x1920", device)
            logging.info("Set Display Size 1080x1920 - OK")
        except Exception as e:
            logging.error(f"Set Display Size to 1080x1920 - Error: : {e}")
        try:
            wm_size_reset(device)
            logging.info("Reset Display Size - OK")
        except Exception as e:
            logging.error(f"Reset Display Size - Error: {e}")

    logging.info("--- Debug Info End ---")
