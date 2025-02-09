import os
import sys

import adbutils._utils
from adbutils import AdbClient, AdbError
from adbutils._device import AdbDevice

import logging
import subprocess

import adb_auto_player.config_loader
from adb_auto_player.exceptions import AdbException


def __set_adb_path():
    is_frozen = hasattr(sys, "frozen") or "__compiled__" in globals()
    logging.debug(f"is_frozen: {is_frozen}")
    if is_frozen and os.name == "nt":
        adb_env_path = os.getenv("ADBUTILS_ADB_PATH")
        if not adb_env_path or not os.path.isfile(adb_env_path):
            adb_path = os.path.join(
                adb_auto_player.config_loader.get_games_dir(), "adb.exe"
            )
            os.environ["ADBUTILS_ADB_PATH"] = adb_path
            adb_env_path = adb_path
        # Dev fallback
        if not adb_env_path or not os.path.isfile(adb_env_path):
            adb_path = os.path.join(
                adb_auto_player.config_loader.get_games_dir().parent,
                "binaries",
                "windows",
                "adb.exe",
            )
            os.environ["ADBUTILS_ADB_PATH"] = adb_path
        logging.debug(f"ADBUTILS_ADB_PATH: {os.getenv("ADBUTILS_ADB_PATH")}")

    if os.name != "nt":
        logging.debug(f"OS: {os.name}")
        try:
            result = subprocess.run(
                ["which", "adb"], capture_output=True, text=True, check=True
            )
            adb_path = result.stdout.strip()
            if not adb_path:
                raise FileNotFoundError("adb not found in system PATH")
            os.environ["ADBUTILS_ADB_PATH"] = adb_path
        except subprocess.CalledProcessError:
            raise FileNotFoundError(
                "Failed to locate adb. Make sure it is installed and in the PATH."
            )
        logging.debug(f"ADBUTILS_ADB_PATH: {os.getenv("ADBUTILS_ADB_PATH")}")

    logging.debug(f"adb_path: {adbutils._utils.adb_path()}")


def get_device() -> AdbDevice:
    """
    :raises AdbException: Device not found
    """
    __set_adb_path()
    main_config = adb_auto_player.config_loader.get_main_config()
    device_id = main_config.get("device", {}).get("ID", "127.0.0.1:7555")
    adb_config = main_config.get("adb", {})
    client = AdbClient(
        host=adb_config.get("host", "127.0.0.1"),
        port=adb_config.get("port", 5037),
    )
    try:
        client.connect(device_id)
    except AdbError as e:
        if "Install adb" in str(e):
            raise e
        else:
            logging.debug(f"client.connect exception: {e}")
    except Exception as e:
        logging.debug(f"client.connect exception: {e}")

    try:
        devices = client.list()
    except Exception:
        raise AdbException("Failed to connect to AdbClient check the config.toml")
    if len(devices) == 0:
        logging.warning("No devices found")
    else:
        devices_str = "Devices:"
        for device_info in devices:
            devices_str += f"\n- {device_info.serial}"
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
