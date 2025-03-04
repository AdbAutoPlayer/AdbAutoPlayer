import os
import sys

import adbutils._utils
from adbutils import AdbClient, AdbError, AdbDevice

import logging
import shutil

import adb_auto_player.config_loader
from adb_auto_player.exceptions import AdbException


def __set_adb_path():
    is_frozen = hasattr(sys, "frozen") or "__compiled__" in globals()
    logging.debug(f"is_frozen: {is_frozen}")
    if is_frozen and os.name == "nt":
        adb_env_path = os.getenv("ADBUTILS_ADB_PATH")
        if not adb_env_path or not os.path.isfile(adb_env_path):
            adb_path = os.path.join(
                adb_auto_player.config_loader.get_binaries_dir(), "adb.exe"
            )
            os.environ["ADBUTILS_ADB_PATH"] = adb_path
            adb_env_path = adb_path
        # Dev fallback
        if not adb_env_path or not os.path.isfile(adb_env_path):
            adb_path = os.path.join(
                adb_auto_player.config_loader.get_binaries_dir(),
                "windows",
                "adb.exe",
            )
            os.environ["ADBUTILS_ADB_PATH"] = adb_path
        logging.debug(f"ADBUTILS_ADB_PATH: {os.getenv('ADBUTILS_ADB_PATH')}")

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
        logging.debug(f"ADBUTILS_ADB_PATH: {os.getenv('ADBUTILS_ADB_PATH')}")

    logging.debug(f"adb_path: {adbutils._utils.adb_path()}")


def get_device(override_size: str | None = None) -> AdbDevice:
    """Connects to an Android device using ADB and returns the device object.

    This function connects to a device by fetching configuration settings,
    handles errors during connection, and returns the device object if found.

    Raises:
        AdbException: Device not found
    """
    __set_adb_path()
    main_config = adb_auto_player.config_loader.get_main_config()
    device_id = main_config.get("device", {}).get("ID", "127.0.0.1:5555")
    adb_config = main_config.get("adb", {})
    client = AdbClient(
        host=adb_config.get("host", "127.0.0.1"),
        port=adb_config.get("port", 5037),
    )

    return __get_adb_device(client, device_id, override_size)


def __get_adb_device(
    client: AdbClient,
    device_id: str,
    override_size: str | None = None,
) -> AdbDevice:
    main_config = adb_auto_player.config_loader.get_main_config()
    wm_size = main_config.get("device", {}).get("wm_size", False)

    try:
        client.connect(device_id)
    except AdbError as e:
        if "Install adb" in str(e):
            raise e
        elif "Unknown data: b" in str(e):
            raise AdbException(
                "Please make sure the adb port is correct "
                "in most cases it should be 5037"
            )
        else:
            logging.debug(f"client.connect exception: {e}")
    except Exception as e:
        logging.debug(f"client.connect exception: {e}")

    device = __connect_to_device(client, device_id)
    if device is None and (
        device_id.startswith("127.0.0.1:") or device_id.startswith("localhost:")
    ):
        i = 1
        host, port = device_id.split(":")
        int_port: int = int(port)
        while i <= 10:
            new_device_id = f"{host}:{int_port + i}"
            logging.debug(f"Trying Device ID: {new_device_id}")
            try:
                device = __connect_to_device(client, new_device_id)
                if device is not None:
                    break
            except AdbException as e:
                logging.debug(f"{e}")
            i += 1

    try:
        devices = client.list()
    except Exception:
        raise AdbException("Failed to connect to AdbClient check the config.toml")
    if len(devices) == 0:
        logging.debug("No devices found")
    else:
        devices_str = "Devices:"
        for device_info in devices:
            devices_str += f"\n- {device_info.serial}"
        logging.debug(devices_str)

    if device:
        logging.debug(f"Connected to Device: {device.serial}")
    elif device is None and len(devices) == 1:
        only_available_device = devices[0].serial
        logging.debug(
            f"{device_id} not found connecting to"
            f" only available Device: {only_available_device}"
        )
        device = __connect_to_device(client, only_available_device)

    if device is None:
        raise AdbException(f"Device: {device_id} not found")

    if override_size and wm_size:
        logging.debug(f"Overriding size: {override_size}")
        try:
            device.shell(f"wm size {override_size}")
        except Exception as e:
            raise AdbException(f"wm size {override_size}: {e}")

    return device


def wm_size_reset(device: AdbDevice | None = None) -> None:
    if device is None:
        device = get_device(override_size=None)

    try:
        device.shell("wm size reset")
    except Exception as e:
        raise AdbException(f"wm size reset: {e}")
    logging.info(f"Reset Display Size for Device: {device.serial}")


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
        logging.debug(f"device.get_state(): {e}")
        return False


def get_screen_resolution(device: AdbDevice) -> str:
    """Uses wm size to resolve device display resolution.

    Raises:
        AdbException: Unable to determine screen resolution
    """
    try:
        result = str(device.shell("wm size"))
    except Exception as e:
        raise AdbException(f"wm size: {e}")
    if result:
        lines = result.splitlines()
        override_size = None
        physical_size = None

        for line in lines:
            if "Override size:" in line:
                override_size = line.split("Override size:")[-1].strip()
                logging.debug(f"Override size: {override_size}")
            elif "Physical size:" in line:
                physical_size = line.split("Physical size:")[-1].strip()
                logging.debug(f"Physical size: {physical_size}")

        resolution_str = override_size if override_size else physical_size

        if resolution_str:
            logging.debug(f"Device screen resolution: {resolution_str}")
            return resolution_str

    logging.debug(result)
    raise AdbException("Unable to determine screen resolution")


def is_portrait(device: AdbDevice) -> bool:
    try:
        orientation_check = device.shell(
            "dumpsys input | grep 'SurfaceOrientation'"
        ).strip()
    except Exception as e:
        raise AdbException(f"dumpsys input: {e}")
    logging.debug(f"orientation_check: {orientation_check}")
    try:
        rotation_check = device.shell("dumpsys window | grep mCurrentRotation").strip()
    except Exception as e:
        raise AdbException(f"dumpsys window: {e}")
    logging.debug(f"rotation_check: {rotation_check}")
    try:
        display_check = device.shell("dumpsys display | grep -E 'orientation'").strip()
    except Exception as e:
        raise AdbException(f"dumpsys display: {e}")
    logging.debug(f"display_check: {display_check}")
    checks = [
        "Orientation: 0" in orientation_check if orientation_check else True,
        "ROTATION_0" in rotation_check if rotation_check else True,
        "orientation=0" in display_check if display_check else True,
    ]

    return all(checks)


def get_running_app(device: AdbDevice) -> str | None:
    app = str(
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
