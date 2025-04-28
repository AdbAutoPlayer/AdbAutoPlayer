"""ADB Auto Player ADB Module."""

import logging
import os
import shutil
import sys
from logging import DEBUG, WARNING
from pathlib import Path
from typing import Any

import adbutils._utils
from adb_auto_player import ConfigLoader, GenericAdbError
from adbutils import AdbClient, AdbDevice, AdbError
from adbutils._proto import AdbDeviceInfo


def _set_adb_path() -> None:
    """Helper function to set environment variable ADBUTILS_ADB_PATH depending on OS.

    Raises:
        FileNotFoundError: ADB executable not found in PATH.
    """
    is_frozen: bool = hasattr(sys, "frozen") or "__compiled__" in globals()

    if is_frozen and os.name == "nt":
        adb_env_path: str | None = os.getenv("ADBUTILS_ADB_PATH")

        if not adb_env_path or not os.path.isfile(adb_env_path):
            candidates: list[Path] = [
                ConfigLoader().binaries_dir / "adb.exe",
                ConfigLoader().binaries_dir / "windows" / "adb.exe",
            ]
            adb_env_path = str(
                next((c for c in candidates if c.exists()), candidates[0])
            )

        os.environ["ADBUTILS_ADB_PATH"] = adb_env_path

    if os.name != "nt":
        logging.debug(f"OS: {os.name}")
        path = os.getenv("PATH")
        paths = [
            "/opt/homebrew/bin",
            "/opt/homebrew/sbin",
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
            "/usr/sbin",
            "/sbin",
        ]

        path_dirs = []
        if path is not None:
            path_dirs = path.split(os.pathsep)
        for p in paths:
            if p not in path_dirs:
                path_dirs.append(p)

        path = os.pathsep.join(path_dirs)
        os.environ["PATH"] = path
        logging.debug(f"PATH: {path}")
        adb_path = shutil.which("adb")
        if not adb_path:
            raise FileNotFoundError("adb not found in system PATH")
        os.environ["ADBUTILS_ADB_PATH"] = adb_path

    logging.debug(f"ADBUTILS_ADB_PATH: {adbutils._utils.adb_path()}")


def get_adb_client() -> AdbClient:
    """Return AdbClient instance."""
    _set_adb_path()
    main_config: dict[str, Any] = ConfigLoader().main_config
    adb_config: Any = main_config.get("adb", {})
    client = AdbClient(
        host=adb_config.get("host", "127.0.0.1"),
        port=adb_config.get("port", 5037),
    )

    logging.debug(f"adb host: {client.host}")
    logging.debug(f"adb port: {client.port}")
    server_version = client.server_version()
    logging.debug(f"adb server_version: {server_version}")
    return client


def get_adb_device(
    override_size: str | None = None,
    adb_client: AdbClient | None = None,
) -> AdbDevice:
    """Connects to an Android device using ADB and returns the device object.

    This function connects to a device by fetching configuration settings,
    handles errors during connection, and returns the device object if found.

    Raises:
        AdbException: Device not found.
    """
    if not adb_client:
        adb_client = get_adb_client()

    main_config: dict[str, Any] = ConfigLoader().main_config
    device_id: Any = main_config.get("device", {}).get("ID", "127.0.0.1:5555")
    return _get_adb_device(adb_client, device_id, override_size)


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
        client.connect(device_id)
    except AdbError as e:
        err_msg = str(e)
        if "Install adb" in err_msg:
            raise e
        elif "Unknown data: b" in err_msg:
            raise GenericAdbError(
                "Please make sure the adb port is correct "
                "(in most cases it should be 5037)"
            )
        else:
            logging.debug(f"client.connect exception: {e}")
    except Exception as e:
        logging.debug(f"client.connect exception: {e}")


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
        raise GenericAdbError(
            "Failed to connect to AdbClient; check the Main Config and "
            "https://AdbAutoPlayer.github.io/AdbAutoPlayer/user-guide/emulator-settings.html"
        )


def log_devices(devices: list[AdbDeviceInfo], log_level: int = DEBUG) -> None:
    """Logs the list of ADB devices.

    Args:
        devices (list[AdbDeviceInfo]): ADB devices.
        log_level (int): Logging level.
    """
    if not devices:
        return
    else:
        devices_str = "Devices: " + ", ".join(
            device_info.serial for device_info in devices
        )
        logging.log(log_level, devices_str)


def _resolve_device(
    client: AdbClient, device_id: str, devices: list[AdbDeviceInfo]
) -> AdbDevice:
    """Attepts to connect to a device.

    Args:
        client (AdbClient): ADB client.
        device_id (str): ADB device ID.
        devices (list[AdbDeviceInfo]): List of ADB devices.

    Raises:
        AdbException: Device not found.

    Returns:
        AdbDevice: Connected device.
    """
    device: AdbDevice | None = _connect_to_device(client, device_id)
    if device is None and len(devices) == 1:
        only_device: str = devices[0].serial
        logging.debug(
            f"{device_id} not found, connecting to only available device: {only_device}"
        )
        device = _connect_to_device(client, only_device)

    if device is None:
        device = _try_incrementing_ports(client, device_id)

    if device is None:
        if not devices:
            logging.warning("No devices found")
        else:
            log_devices(devices, WARNING)
        raise GenericAdbError(f"Device: {device_id} not found")
    return device


def _try_incrementing_ports(client: AdbClient, device_id: str) -> AdbDevice | None:
    """Attempts to connect to a device by incrementing the port number.

    This is specifically for cases where Bluestacks prompts the user to create a
    new instance with a different Android version. Even after closing the first
    instance, it may remain in the device list but not be connectable. This function
    tries the next 5 ports to find a valid connection.
    """
    if ":" in device_id:
        address, port_str = device_id.rsplit(":", 1)
        if port_str.isdigit():
            port = int(port_str) + 1
            # 5556-5559 in case emulator used increments by 1
            for port_increment in range(4):
                new_device_id = f"{address}:{port + port_increment}"
                device = _connect_to_device(client, new_device_id)
                if device is not None:
                    return device
        if port_str == "5555":
            # BlueStacks 5 seems to increment by 10 for the next port
            for port in [5565, 5575, 5585]:
                new_device_id = f"{address}:{port}"
                device = _connect_to_device(client, new_device_id)
                if device is not None:
                    return device
    return None


def _override_size(device: AdbDevice, override_size: str) -> None:
    logging.debug(f"Overriding size: {override_size}")
    try:
        output = device.shell(f"wm size {override_size}")
        if "java.lang.SecurityException" in output:
            raise GenericAdbError("java.lang.SecurityException")
    except Exception as e:
        logging.debug(f"wm size {override_size} Error: {e}")
        raise GenericAdbError(f"Error overriding size: {e}")


def _get_adb_device(
    client: AdbClient, device_id: str, override_size: str | None = None
) -> AdbDevice:
    """Connects to a specified ADB device and optionally overrides its screen size.

    This function uses the provided ADB client and device ID to connect to
    an Android device. It logs the available devices, resolves the correct
    device to connect to, and logs the connection. Optionally, it can override
    the device's screen size if specified.

    Args:
        client (AdbClient): ADB client used for the connection.
        device_id (str): ID of the device to connect to.
        override_size (str | None, optional): Screen size to override.

    Raises:
        AdbException: If unable to connect to the device or if size override fails.

    Returns:
        AdbDevice: Connected ADB device.
    """
    # Get configuration for window size override
    main_config: dict[str, Any] = ConfigLoader().main_config
    wm_size: Any = main_config.get("device", {}).get("wm_size", False)

    # Connect the client and list devices
    _connect_client(client, device_id)
    devices: list[AdbDeviceInfo] = _get_devices(client)
    log_devices(devices)

    # Try to resolve the correct device
    device = _resolve_device(client, device_id, devices)
    logging.debug(f"Connected to Device: {device.serial}")

    # Optionally override the size
    if override_size and wm_size:
        _override_size(device, override_size)

    return device


def exec_wm_size(resolution: str, device: AdbDevice | None = None) -> None:
    """Sets display size to resolution.

    Some games will not automatically scale when the resolution changes.
    This can be used to set the resolution before starting the game for phones.

    Args:
        resolution (str): Display size to use.
        device (AdbDevice | None): ADB device.
    """
    if device is None:
        device = get_adb_device(override_size=None)

    _override_size(device, resolution)
    logging.info(f"Set Display Size to {resolution} for Device: {device.serial}")


def wm_size_reset(device: AdbDevice | None = None) -> None:
    """Resets the display size of the device to its original size.

    Uses a shell command to reset the display size.
    If device is not specified, it will use the device from get_device().

    Args:
        device (AdbDevice | None): ADB device.

    Raises:
        AdbException: Unable to reset display size.
    """
    if device is None:
        device = get_adb_device(override_size=None)

    try:
        device.shell("wm size reset")
    except Exception as e:
        raise GenericAdbError(f"wm size reset: {e}")
    logging.info(f"Reset Display Size for Device: {device.serial}")


def _connect_to_device(client: AdbClient, device_id: str) -> AdbDevice | None:
    """Helper function to return a connected device.

    Args:
        client (AdbClient): ADB client.
        device_id (str): ADB device ID.

    Returns:
        AdbDevice | None: Connected device.
    """
    try:
        _connect_client(client, device_id)
    except Exception:
        return None
    device: AdbDevice = client.device(f"{device_id}")
    if _is_device_connection_active(device):
        return device
    else:
        return None


def _is_device_connection_active(device: AdbDevice) -> bool:
    """Helper function to check if device connection is active.

    Args:
        device (AdbDevice): ADB Device.

    Returns:
        bool: True if device connection is active, False otherwise.
    """
    try:
        device.get_state()
        return True
    except Exception as e:
        logging.debug(f"device.get_state(): {e}")
        return False


def get_screen_resolution(device: AdbDevice) -> str:
    """Get screen resolution as string.

    Args:
        device (AdbDevice): ADB device.

    Raises:
        AdbException: Unable to determine screen resolution.

    Returns:
        str: Resolution as string.
    """
    try:
        result = str(device.shell("wm size"))
    except Exception as e:
        raise GenericAdbError(f"wm size: {e}")
    if result:
        lines: list[str] = result.splitlines()
        override_size = None
        physical_size = None

        for line in lines:
            if "Override size:" in line:
                override_size = line.split("Override size:")[-1].strip()
                logging.debug(f"Override size: {override_size}")
            elif "Physical size:" in line:
                physical_size = line.split("Physical size:")[-1].strip()
                logging.debug(f"Physical size: {physical_size}")

        resolution_str: str | None = override_size if override_size else physical_size

        if resolution_str:
            logging.debug(f"Device screen resolution: {resolution_str}")
            if is_portrait(device):
                return resolution_str
            else:
                width, height = resolution_str.split("x")
                return f"{height}x{width}"
    logging.debug(result)
    raise GenericAdbError("Unable to determine screen resolution")


def is_portrait(device: AdbDevice) -> bool:
    """Check if device is in portrait mode.

    Args:
        device (AdbDevice): ADB device.

    Returns:
        bool: True if all checks pass, False otherwise.
    """
    try:
        orientation_check = device.shell(
            "dumpsys input | grep 'SurfaceOrientation'"
        ).strip()
    except Exception as e:
        raise GenericAdbError(f"dumpsys input: {e}")
    logging.debug(f"orientation_check: {orientation_check}")

    try:
        rotation_check = device.shell("dumpsys window | grep mCurrentRotation").strip()
    except Exception as e:
        raise GenericAdbError(f"dumpsys window: {e}")
    logging.debug(f"rotation_check: {rotation_check}")

    try:
        display_check = device.shell("dumpsys display | grep -E 'orientation'").strip()
    except Exception as e:
        raise GenericAdbError(f"dumpsys display: {e}")
    logging.debug(f"display_check: {display_check}")

    checks: list[bool] = [
        "Orientation: 0" in orientation_check if orientation_check else True,
        "ROTATION_0" in rotation_check if rotation_check else True,
        "orientation=0" in display_check if display_check else True,
    ]

    return all(checks)


def get_running_app(device: AdbDevice) -> str | None:
    """Get the currently running app.

    Args:
        device (AdbDevice): ADB device.

    Returns:
        str | None: Currently running app name, or None if unable to determine.
    """
    app: str = str(
        device.shell(
            "dumpsys activity activities | grep mResumedActivity | "
            'cut -d "{" -f2 | cut -d \' \' -f3 | cut -d "/" -f1'
        )
    ).strip()
    # Not sure why this happens
    # encountered when running on Apple M1 Max using MuMu Player
    if not app:
        app = str(
            device.shell(
                "dumpsys activity activities | grep ResumedActivity | "
                'cut -d "{" -f2 | cut -d \' \' -f3 | cut -d "/" -f1'
            )
        ).strip()
        if "\n" in app:
            app = app.split("\n")[0]
    if app:
        logging.debug(f"Currently running app: {app}")
        return str(app)
    return None
