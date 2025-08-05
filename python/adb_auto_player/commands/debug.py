"""Debug Commands."""

import logging
import pprint
import time

from adb_auto_player.decorators import register_command
from adb_auto_player.device.adb import AdbClientHelper, AdbController
from adb_auto_player.models.geometry import PointOutsideDisplay
from adb_auto_player.settings import ConfigLoader
from adbutils import AdbClient


@register_command(
    gui=None,  # This is hard coded in the GUI so we do not need it.
    name="Debug",
)
def _log_debug() -> None:
    logging.getLogger().setLevel(logging.DEBUG)
    logging.info("--- Debug Info Start ---")
    _log_main_config()
    if not _get_and_log_adb_client():
        logging.warning("ADB client could not be initialized.")
        logging.info("--- Debug Info End ---")
        return

    logging.info("--- ADB Controller ---")
    try:
        controller = AdbController()
    except Exception as e:
        logging.error(f"Error: {e}")
        logging.warning("ADB device could not be resolved.")
        logging.info("--- Debug Info End ---")
        return

    _log_device_info(controller)
    _test_input_delay(controller)
    _log_display_info(controller)
    _test_resize_display(controller)

    logging.info("--- Debug Info End ---")
    return


def _log_main_config() -> None:
    logging.info("--- General Settings ---")
    logging.info(f"{pprint.pformat(ConfigLoader.general_settings())}")


def _get_and_log_adb_client() -> AdbClient | None:
    logging.info("--- ADB Client ---")
    try:
        client = AdbClientHelper.get_adb_client()
        AdbClientHelper.log_devices(client.list(), logging.INFO)
        return client
    except Exception as e:
        logging.error(f"Error: {e}")
    return None


def _log_device_info(controller: AdbController) -> None:
    logging.info("--- Device Info ---")
    logging.info(f"Device Serial: {controller.d.serial}")
    logging.info(f"Device Info: {controller.d.info}")
    _ = controller.get_running_app()


def _test_input_delay(controller: AdbController) -> None:
    logging.info("--- Testing Input Delay ---")
    total_time = 0.0
    iterations = 10
    for _ in range(iterations):
        start_time = time.time()
        controller.tap(PointOutsideDisplay())
        total_time += (time.time() - start_time) * 1000
    average_time = total_time / iterations
    logging.info(
        f"Average time to tap screen over {iterations} attempts: {average_time:.2f} ms"
    )


def _log_display_info(controller: AdbController) -> None:
    logging.info("--- Device Display ---")
    display_info = controller.get_display_info()
    logging.info(f"Resolution: {display_info.width}x{display_info.height}")
    logging.info(f"Orientation: {display_info.orientation}")


def _test_resize_display(controller: AdbController) -> None:
    logging.info("--- Test Resize Display ---")
    try:
        controller.set_display_size("1080x1920")
        logging.info("Set Display Size 1080x1920 - OK")
    except Exception as e:
        logging.error(f"{e}", exc_info=True)
    try:
        controller.reset_display_size()
        logging.info("Reset Display Size - OK")
    except Exception as e:
        logging.error(f"Reset Display Size - Error: {e}")
