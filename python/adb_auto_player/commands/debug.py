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
from adb_auto_player.decorators.register_command import register_command
from adbutils import AdbClient, AdbDevice


@register_command(
    gui=None,  # This is hard coded in the GUI so we do not need it.
    name="Debug",
)
def _log_debug() -> None:
    logging.info("--- Debug Info Start ---")
    _log_main_config()
    client = _get_and_log_adb_client()
    if not client:
        logging.warning("ADB client could not be initialized.")
        logging.info("--- Debug Info End ---")
        return

    device = _get_and_log_adb_device(client)
    if not device:
        logging.warning("ADB device could not be resolved.")
        logging.info("--- Debug Info End ---")
        return
    _log_device_info(device)
    _test_input_delay(device)
    _log_display_info(device)
    _test_resize_display(device)

    logging.info("--- Debug Info End ---")
    return


def _log_main_config() -> None:
    logging.info("--- Main Config ---")
    config = ConfigLoader().main_config
    logging.info(f"Config: {pprint.pformat(config)}")


def _get_and_log_adb_client() -> AdbClient | None:
    logging.info("--- ADB Client ---")
    try:
        client = get_adb_client()
        log_devices(client.list(), logging.INFO)
        return client
    except Exception as e:
        logging.error(f"Error: {e}")
    return None


def _get_and_log_adb_device(client: AdbClient) -> AdbDevice | None:
    logging.info("--- ADB Device ---")
    try:
        return get_adb_device(adb_client=client)
    except Exception as e:
        logging.error(f"Error: {e}")
    return None


def _log_device_info(device):
    logging.info("--- Device Info ---")
    logging.info(f"Device Serial: {device.serial}")
    logging.info(f"Device Info: {device.info}")
    _ = get_running_app(device)


def _test_input_delay(device) -> None:
    logging.info("--- Testing Input Delay ---")
    total_time = 0.0
    iterations = 10
    for _ in range(iterations):
        start_time = time.time()
        device.click(-1, -1)
        total_time += (time.time() - start_time) * 1000
    average_time = total_time / iterations
    logging.info(
        f"Average time taken to tap screen {iterations} times: {average_time:.2f} ms"
    )


def _log_display_info(device) -> None:
    logging.info("--- Device Display ---")
    display_info = get_display_info(device)
    logging.info(f"Resolution: {display_info.width}x{display_info.height}")
    logging.info(f"Orientation: {display_info.orientation}")


def _test_resize_display(device) -> None:
    logging.info("--- Test Resize Display ---")
    try:
        exec_wm_size("1080x1920", device)
        logging.info("Set Display Size 1080x1920 - OK")
    except Exception as e:
        if "java.lang.SecurityException" in str(e):
            logging.error(
                "Missing permissions, check if your device has settings, such as: "
                '"USB debugging (Security settings)" and enable them.'
            )
        else:
            logging.error(f"{e}", exc_info=True)
    try:
        wm_size_reset(device)
        logging.info("Reset Display Size - OK")
    except Exception as e:
        logging.error(f"Reset Display Size - Error: {e}")
