from adbutils import AdbClient
from adbutils._device import AdbDevice

import logging

import adb_auto_player.config_loader
from adb_auto_player.exceptions import AdbException


def get_device() -> AdbDevice:
    """
    :raises AdbException: Device not found
    """
    main_config = adb_auto_player.config_loader.get_main_config()
    device_id = main_config.get("device", {}).get("ID", "127.0.0.1:5555")
    adb_config = main_config.get("adb", {})
    client = AdbClient(
        host=adb_config.get("host", "127.0.0.1"),
        port=adb_config.get("port", 5037),
    )
    try:
        client.connect(device_id)
    except Exception:
        pass
    try:
        devices = client.list()
    except Exception:
        raise AdbException("Failed to connect to AdbClient check the main_config.toml")
    if len(devices) == 0:
        logging.warning("No devices found")
    else:
        devices_str = "Devices:"
        for device_info in devices:
            devices_str += f"\n{device_info.serial}"
        logging.info(devices_str)

    device = __connect_to_device(client, device_id)
    if device is None and len(devices) == 1:
        only_available_device = devices[0].serial
        logging.warning(
            f"{device_id} not found connecting to"
            f" only available device: {only_available_device}"
        )
        device = __connect_to_device(client, only_available_device)

    if device is None:
        raise AdbException(f"Device: {device_id} not found")

    logging.info(f"Successfully connected to device {device.serial}")
    return device


def __connect_to_device(client: AdbClient, device_id: str) -> AdbDevice | None:
    device = client.device(f"{device_id}")
    if is_device_connection_active(device):
        return device
    else:
        return None


def is_device_connection_active(device: AdbDevice) -> bool:
    try:
        device.get_state()
        return True
    except Exception as e:
        logging.debug(f"Exception: {e}")
        return False


def get_screen_resolution(device: AdbDevice) -> str:
    """
    :raises AdbException: Unable to determine screen resolution
    """
    result = str(device.shell("wm size"))
    if result:
        resolution_str = result.split("Physical size: ")[-1].strip()
        logging.debug(f"Device screen resolution: {resolution_str}")
        return str(resolution_str)
    logging.debug(result)
    raise AdbException("Unable to determine screen resolution")
