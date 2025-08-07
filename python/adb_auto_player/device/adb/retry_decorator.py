import logging
import time
from collections.abc import Callable
from functools import wraps

import psutil
from adb_auto_player.exceptions import GenericAdbUnrecoverableError
from adbutils import AdbDevice

from .adb_client import AdbClientHelper


def adb_retry(func: Callable) -> Callable:
    """Decorator that adds retry logic with ADB process killing.

    1. Try 2 times normally
    2. If that fails, kill ADB server and recreate device
    3. Try 2 more times
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, "d"):
            raise AttributeError(
                "@adb_retry decorator requires the class to have a 'd' attribute. "
                f"Class {self.__class__.__name__} does not have this attribute."
            )

        if not isinstance(self.d, AdbDevice):
            raise TypeError(
                f"@adb_retry decorator requires 'd' attribute to be an AdbDevice "
                "instance. "
                f"Got {type(self.d).__name__} instead."
            )

        last_exception = None

        # First 2 attempts
        for attempt in range(2):
            try:
                return func(self, *args, **kwargs)
            except GenericAdbUnrecoverableError as e:
                raise e
            except Exception as e:
                last_exception = e
                logging.debug(f"{func.__name__} attempt {attempt + 1} failed: {e}")
                if attempt < 1:
                    time.sleep(1)

        logging.debug(
            f"{func.__name__} initial attempts failed, "
            "attempting to restart ADB server and recreate device"
        )
        _restart_adb_server()

        new_device = _recreate_device(self.d)
        if new_device is not None:
            self.d = new_device
            logging.debug("Device recreated successfully")
        else:
            raise GenericAdbUnrecoverableError(
                f"ADB connection failed multiple times. Last error: {last_exception}"
            )

        for attempt in range(2):
            try:
                return func(self, *args, **kwargs)
            except GenericAdbUnrecoverableError as e:
                raise e
            except Exception as e:
                last_exception = e
                logging.debug(
                    f"{func.__name__} final attempt {attempt + 1} failed: {e}"
                )
                if attempt < 1:  # Don't sleep on the last attempt
                    time.sleep(1)

        raise GenericAdbUnrecoverableError(
            f"ADB connection failed multiple times. Last error: {last_exception}"
        )

    return wrapper


def _recreate_device(d: AdbDevice) -> AdbDevice | None:
    if d.serial is None:
        return None
    return AdbClientHelper.get_adb_device(d.serial)


def _restart_adb_server() -> None:
    """Restart ADB server, first trying kill-server command, then process killing."""
    if _try_adb_kill_server():
        logging.debug("ADB server killed successfully using kill-server command")
        return

    logging.debug("kill-server command failed, attempting to kill ADB process directly")
    _kill_adb_process()
    return


def _try_adb_kill_server() -> bool:
    """Try to kill ADB server using adb kill-server command.

    Returns:
        True if successful, False otherwise
    """
    try:
        AdbClientHelper.get_adb_client().server_kill()
        return True
    except Exception as e:
        logging.debug(f"adb kill-server command failed: {e}")
        return False


def _kill_adb_process() -> None:
    """Kill the ADB process directly using psutil."""
    for proc in psutil.process_iter(["name"]):
        if proc.info["name"].lower() in ["adb", "adb.exe"]:
            try:
                proc.terminate()
                proc.wait(timeout=3)
                logging.debug("ADB process terminated successfully")
                return
            except psutil.NoSuchProcess:
                return
            except psutil.TimeoutExpired:
                proc.kill()
                logging.debug("ADB process killed forcefully")
                return
            except psutil.AccessDenied:
                raise GenericAdbUnrecoverableError(
                    "Access Denied: cannot restart ADB Server."
                )
    return
