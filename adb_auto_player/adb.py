import adb_auto_player.logger as logging
from typing import Dict, Any, NoReturn
from adbutils._device import AdbDevice
from adbutils import AdbClient


def get_device(main_config: Dict[str, Any]) -> AdbDevice | NoReturn:
    device_id = main_config.get("device", {}).get("id", "127.0.0.1:5555")

    adb_config = main_config.get("adb", {})

    client = AdbClient(
        host=adb_config.get("host", "127.0.0.1"),
        port=adb_config.get("port", 5037),
    )

    try:
        devices = client.list()
        if len(devices) == 0:
            raise RuntimeError("No devices found")

        devices_str = "Devices:"
        for device_info in devices:
            devices_str += f"\n{device_info.serial}"

        logging.info(devices_str)

        device = client.device(f"{device_id}")

        if device is None:
            raise LookupError(f"{device_id} not found")

        device.get_state()
        logging.info(f"Successfully connected to device {device_id}")
        return device
    except Exception as e:
        logging.critical_and_exit(f"Failed to connect to device: {e}")


def get_currently_running_app(device: AdbDevice) -> str | NoReturn:
    try:
        app = str(
            device.shell(
                "dumpsys activity activities | grep mResumedActivity | "
                'cut -d "{" -f2 | cut -d \' \' -f3 | cut -d "/" -f1'
            )
        ).strip()

        if app:
            logging.info(f"Currently running app: {app}")
            return str(app)

        raise ValueError("Unable to determine the currently running app")
    except Exception as e:
        logging.critical_and_exit(f"Error while retrieving currently running app: {e}")


def get_screen_resolution(device: AdbDevice) -> str | NoReturn:
    try:
        result = str(device.shell("wm size"))

        if result:
            resolution_str = result.split("Physical size: ")[-1].strip()
            logging.info(f"Device screen resolution: {resolution_str}")

            return str(resolution_str)

        raise ValueError("No display information found")
    except Exception as e:
        logging.critical_and_exit(f"Error while retrieving screen resolution: {e}")
