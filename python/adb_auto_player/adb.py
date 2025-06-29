"""ADB Auto Player ADB Module.

TODO adb in its own module?
"""

import logging
import os
import shutil
import sys
from dataclasses import dataclass
from enum import StrEnum
from logging import DEBUG, WARNING
from pathlib import Path
from typing import Any

import adbutils._utils
from adb_auto_player.exceptions import GenericAdbError, GenericAdbUnrecoverableError
from adb_auto_player.util import ConfigLoader
from adbutils import AdbClient, AdbDevice, AdbError
from adbutils._proto import AdbDeviceInfo


class Orientation(StrEnum):
    """Device orientation enumeration."""

    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


@dataclass
class DisplayInfo:
    """Data class containing device display information."""

    width: int
    height: int
    orientation: Orientation


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

    server_version = client.server_version()

    logging.debug(
        "ADB Client "
        f"host: {client.host}, "
        f"port: {client.port}, "
        f"server_version: {server_version}"
    )
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
        output = client.connect(device_id)
        if "cannot connect" in output:
            raise GenericAdbError(output)
    except GenericAdbUnrecoverableError as e:
        logging.error(f"{e}")
        sys.exit(1)
    except GenericAdbError as e:
        logging.debug(f"{e}")
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
            logging.error(f"client.connect AdbError: {e}")
    except Exception as e:
        logging.error(f"client.connect exception: {e}")


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


def _resolve_device(
    client: AdbClient,
    device_id: str,
) -> AdbDevice:
    """Attempts to connect to a specific ADB device.

    Args:
        client (AdbClient): ADB client.
        device_id (str): Expected ADB device ID to connect to.

    Raises:
        GenericAdbUnrecoverableError: If the device cannot be resolved.

    Returns:
        AdbDevice: Connected device instance.
    """
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
            log_devices(devices, WARNING)
        raise GenericAdbUnrecoverableError(
            f"Unable to resolve ADB device. Device ID '{device_id}' not found. "
            f"Make sure the device is connected and ADB is enabled."
        )

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
        "127.0.0.1:7555",
        "127.0.0.1:7565",
        "127.0.0.1:7556",
        "127.0.0.1:5555",
        "127.0.0.1:5565",
        "127.0.0.1:5556",
        "emulator-5554",
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


def _override_size(device: AdbDevice, override_size: str) -> None:
    logging.debug(f"Overriding size: {override_size}")
    try:
        output = device.shell(f"wm size {override_size}")
    except Exception as e:
        logging.debug(f"wm size {override_size} Error: {e}")
        raise GenericAdbError(f"Error overriding size: {e}")

    if "java.lang.SecurityException" in output:
        logging.debug(f"wm size {override_size} Error: {output}")
        raise GenericAdbUnrecoverableError("java.lang.SecurityException")


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

    # Try to resolve the correct device
    device = _resolve_device(client, device_id)
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
        logging.debug(f"state(): {e}")
        return False


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


def get_display_info(device: AdbDevice) -> DisplayInfo:
    """Get display resolution and orientation.

    Args:
        device (AdbDevice): ADB device.

    Raises:
        GenericAdbUnrecoverableError: Unable to determine screen resolution or
            orientation.

    Returns:
        DisplayInfo: Resolution and orientation.
    """
    try:
        result = str(device.shell("wm size", timeout=5))
    except Exception as e:
        raise GenericAdbUnrecoverableError(f"wm size: {e}")

    if not result:
        raise GenericAdbUnrecoverableError("Unable to determine screen resolution")

    # Parse resolution from wm size output
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

    if not resolution_str:
        raise GenericAdbUnrecoverableError(
            f"Unable to determine screen resolution: {result}"
        )

    try:
        width_str, height_str = resolution_str.split("x")
        width, height = int(width_str), int(height_str)
    except (ValueError, AttributeError):
        raise GenericAdbUnrecoverableError(
            f"Invalid resolution format: {resolution_str}"
        )

    device_orientation = _check_orientation(device)

    return DisplayInfo(
        width=width if Orientation.PORTRAIT == device_orientation else height,
        height=height if Orientation.PORTRAIT == device_orientation else width,
        orientation=device_orientation,
    )


def _check_orientation(device: AdbDevice) -> Orientation:
    """Check device orientation using multiple fallback methods.

    Tries different orientation detection methods in order of reliability,
    returning as soon as a definitive result is found. Portrait orientation
    corresponds to rotation 0, while landscape corresponds to rotations 1 and 3.

    Args:
        device (AdbDevice): ADB device.

    Returns:
        Orientation: Device orientation (PORTRAIT or LANDSCAPE).

    Raises:
        GenericAdbUnrecoverableError: If unable to perform any orientation checks.
    """
    # Check 1: SurfaceOrientation (most reliable)
    try:
        orientation_check = device.shell(
            "dumpsys input | grep 'SurfaceOrientation'"
        ).strip()
        logging.debug(f"orientation_check: {orientation_check}")
        if orientation_check:
            if "Orientation: 0" in orientation_check:
                return Orientation.PORTRAIT
            elif any(
                x in orientation_check for x in ["Orientation: 1", "Orientation: 3"]
            ):
                return Orientation.LANDSCAPE
    except Exception as e:
        logging.debug(f"SurfaceOrientation check failed: {e}")

    # Check 2: Current rotation (fallback)
    try:
        rotation_check = device.shell("dumpsys window | grep mCurrentRotation").strip()
        logging.debug(f"rotation_check: {rotation_check}")
        if rotation_check:
            if "ROTATION_0" in rotation_check:
                return Orientation.PORTRAIT
            elif any(x in rotation_check for x in ["ROTATION_90", "ROTATION_270"]):
                return Orientation.LANDSCAPE
    except Exception as e:
        logging.debug(f"Rotation check failed: {e}")

    # Check 3: Display orientation (last resort)
    try:
        display_check = device.shell("dumpsys display | grep -E 'orientation'").strip()
        logging.debug(f"display_check: {display_check}")
        if display_check:
            if "orientation=0" in display_check:
                return Orientation.PORTRAIT
            elif any(x in display_check for x in ["orientation=1", "orientation=3"]):
                return Orientation.LANDSCAPE
    except Exception as e:
        logging.debug(f"Display orientation check failed: {e}")

    raise GenericAdbUnrecoverableError("Unable to determine device orientation")
