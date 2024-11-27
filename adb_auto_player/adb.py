import logging
from typing import Dict, Any

from ppadb.client import Client as AdbClient
from ppadb.device import Device


def get_device(main_config: Dict[str, Any]) -> Device:
    device_id = main_config.get("device", {}).get("id", "127.0.0.1:5555")

    adb_config = main_config.get("adb", {})

    client = AdbClient(
        host=adb_config.get("host", "127.0.0.1"),
        port=adb_config.get("port", 5037),
    )
    device = client.device(f"{device_id}")

    try:
        device.get_state()
        logging.info(f"Successfully connected to device {device_id}")
        return device
    except Exception as e:
        logging.critical(f"Failed to connect to device: {e}")


def get_currently_running_app(device: Device) -> str:
    try:
        app = device.shell(
            "dumpsys activity activities | grep mResumedActivity | "
            'cut -d "{" -f2 | cut -d \' \' -f3 | cut -d "/" -f1'
        ).strip()

        if app:
            logging.info(f"Currently running app: {app}")
            return str(app)

        raise ValueError("Unable to determine the currently running app")
    except Exception as e:
        logging.critical(f"Error while retrieving currently running app: {e}")


def get_screen_resolution(device: Device) -> str:
    try:
        result = device.shell("wm size")

        if result:
            resolution_str = result.split("Physical size: ")[-1].strip()
            logging.info(f"Device screen resolution: {resolution_str}")

            return str(resolution_str)

        raise ValueError("No display information found.")
    except Exception as e:
        logging.critical(f"Error while retrieving screen resolution: {e}")
