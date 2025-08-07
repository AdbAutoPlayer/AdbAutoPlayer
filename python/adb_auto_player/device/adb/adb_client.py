import logging
from functools import lru_cache
from logging import DEBUG, WARNING

from adb_auto_player.decorators import register_cache
from adb_auto_player.exceptions import GenericAdbError, GenericAdbUnrecoverableError
from adb_auto_player.models.decorators import CacheGroup
from adb_auto_player.settings import ConfigLoader
from adbutils import AdbClient, AdbDevice, AdbError
from adbutils._proto import AdbDeviceInfo

from .adb_utils import _set_adb_path


class AdbClientHelper:
    """Helper functions to get AdbClient or AdbDevice."""

    @staticmethod
    def get_adb_device(device_id: str) -> AdbDevice | None:
        """Get active AdbDevice if it exists."""
        client: AdbClient = AdbClientHelper.get_adb_client()
        return _connect_to_device(client, device_id)

    @staticmethod
    @register_cache(CacheGroup.ADB)
    @lru_cache(maxsize=1)
    def get_adb_client() -> AdbClient:
        """Return AdbClient instance."""
        _set_adb_path()
        advanced_settings = ConfigLoader.general_settings().advanced
        client = AdbClient(
            host=advanced_settings.adb_host,
            port=advanced_settings.adb_port,
        )

        server_version = client.server_version()

        logging.debug(
            "ADB Client "
            f"host: {client.host}, "
            f"port: {client.port}, "
            f"server_version: {server_version}"
        )
        return client

    @staticmethod
    @register_cache(CacheGroup.ADB)
    @lru_cache(maxsize=1)
    def resolve_adb_device() -> AdbDevice:
        """Connects to an Android device using ADB and returns the device object.

        This function connects to a device by fetching configuration settings,
        handles errors during connection, and returns the device object if found.

        Raises:
            AdbException: Device not found.
        """
        adb_client = AdbClientHelper.get_adb_client()
        return _resolve_device(adb_client)

    @staticmethod
    def log_devices(devices: list[AdbDeviceInfo], log_level: int = DEBUG) -> None:
        """Logs the list of ADB devices.

        Args:
            devices (list[AdbDeviceInfo]): ADB devices.
            log_level (int): Logging level.
        """
        if not devices:
            logging.log(log_level, "No devices found.")
            return
        else:
            devices_str = "Devices: " + ", ".join(
                device_info.serial for device_info in devices
            )
            logging.log(log_level, devices_str)


def _connect_client(client: AdbClient, device_id: str) -> None:
    """Attempts to connect to an ADB device using the given client and device ID.

    Args:
        client (AdbClient): ADB client instance used for connection.
        device_id (str): ID of the device to connect to.

    Raises:
        AdbError: AdbTimeout error regarding installation or port mismatch.
        AdbException: Other AdbTimeout errors.
    """
    try:
        output = client.connect(device_id)
        if "cannot connect" in output:
            raise GenericAdbError(output)
    except GenericAdbUnrecoverableError as e:
        raise e
    except GenericAdbError as e:
        raise e
    except AdbError as e:
        err_msg = str(e)
        if "Install adb" in err_msg:
            raise GenericAdbUnrecoverableError(err_msg)
        elif "Unknown data: b" in err_msg:
            raise GenericAdbUnrecoverableError(
                "Please make sure the adb port is correct "
                "(in most cases it should be 5037)"
            )
        else:
            raise GenericAdbError(e)
    except Exception as e:
        raise GenericAdbError(e)


def _get_devices(client: AdbClient) -> list[AdbDeviceInfo]:
    """Attempts to list ADB devices.

    Args:
        client (AdbClient): ADB client instance used for connection.

    Raises:
        AdbException: Failed to list devices.

    Returns:
        list[AdbDeviceInfo]: List of devices.
    """
    try:
        return client.list()
    except Exception as e:
        logging.debug(f"client.list exception: {e}")
        raise GenericAdbUnrecoverableError(
            "Failed to connect to AdbClient; check the General Settings and "
            "https://AdbAutoPlayer.github.io/AdbAutoPlayer/user-guide/emulator-settings.html"
        )


def _resolve_device(
    client: AdbClient,
) -> AdbDevice:
    """Attempts to connect to a specific ADB device.

    Args:
        client (AdbClient): ADB client.

    Raises:
        GenericAdbUnrecoverableError: If the device cannot be resolved.

    Returns:
        AdbDevice: Connected device instance.
    """
    device_id = ConfigLoader.general_settings().device.id
    device: AdbDevice | None = _connect_to_device(client, device_id)
    devices: list[AdbDeviceInfo] = _get_devices(client)

    if device is None and len(devices) == 1:
        only_device: str = devices[0].serial
        logging.debug(
            f"Device '{device_id}' not found. "
            f"Only one device connected: '{only_device}'. Trying to use it."
        )
        device = _connect_to_device(client, only_device)

    if device is None:
        logging.debug(
            f"Device '{device_id}' not found. "
            "Attempting to resolve using common device IDs..."
        )
        device = _try_common_ports_and_device_ids(client, checked_device_id=device_id)

    if device is None:
        if not devices:
            logging.warning("No devices found")
        else:
            AdbClientHelper.log_devices(devices, WARNING)
        raise GenericAdbUnrecoverableError(
            f"Unable to resolve ADB device. Device ID '{device_id}' not found. "
            f"Make sure the device is connected, ADB is enabled and check the "
            f"`Show Debug info` button."
        )

    logging.debug(f"Connected to Device: {device.serial}")
    return device


def _try_common_ports_and_device_ids(
    client: AdbClient, checked_device_id: str
) -> AdbDevice | None:
    """Attempts to connect to a device by using common ports and device IDs.

    This is specifically for people who did not read the user guide.
    And also for cases where Bluestacks prompts the user to create a
    new instance with a different Android version. Even after closing the first
    instance, it may remain in the device list but not be connectable.
    """
    logging.debug("Trying common device ids")
    common_device_ids: list[str] = [
        "127.0.0.1:5555",
        "emulator-5554",
        "127.0.0.1:7555",
        "127.0.0.1:7565",
        "127.0.0.1:7556",
        "127.0.0.1:5565",
        "127.0.0.1:5556",
        "emulator-5555",
    ]

    # Remove already checked device ID
    if checked_device_id in common_device_ids:
        common_device_ids.remove(checked_device_id)

    for potential_device_id in common_device_ids:
        device = _connect_to_device(client, potential_device_id)
        if device is not None:
            return device

    return None


def _connect_to_device(client: AdbClient, device_id: str) -> AdbDevice | None:
    try:
        _connect_client(client, device_id)
    except GenericAdbError:
        pass
    device: AdbDevice = client.device(f"{device_id}")
    if _is_device_connection_active(device):
        return device
    else:
        return None


def _is_device_connection_active(device: AdbDevice) -> bool:
    try:
        device.get_state()
        return True
    except Exception as e:
        logging.debug(f"state(): {e}")
        return False
