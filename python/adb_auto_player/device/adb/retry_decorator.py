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
    2. If that fails, kill ADB process and recreate device
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
            "killing ADB process and recreating device"
        )
        _kill_adb_process()

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


def _kill_adb_process():
    """Kill the ADB process directly instead of using adb kill-server."""
    for proc in psutil.process_iter(["name"]):
        if proc.info["name"].lower() in ["adb", "adb.exe"]:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except psutil.NoSuchProcess:
                return
            except psutil.TimeoutExpired:
                proc.kill()
            except psutil.AccessDenied:
                raise GenericAdbUnrecoverableError(
                    "Access Denied: cannot restart ADB Server."
                )
