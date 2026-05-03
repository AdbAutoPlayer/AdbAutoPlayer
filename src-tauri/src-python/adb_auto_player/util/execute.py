"""This module provides a utility function `execute` to safely invoke callable objects.

The `execute` function handles both bound and unbound methods, automatically
instantiating classes if necessary. It captures and logs exceptions, with special
handling for `GenericAdbError` related to Android Debug Bridge permissions.

Usage:
    - Call `execute` with a function and optionally an instance and kwargs.
    - Returns any exception encountered during execution, or None if successful.

This utility simplifies error handling and invocation of callables that may require
an instance context or special error processing.
"""

import _thread
import importlib
import inspect
import logging
import sys
import threading
import time
import tomllib
from collections.abc import Callable
from typing import Any, cast

from adb_auto_player.exceptions import AutoPlayerError, GenericAdbUnrecoverableError
from adb_auto_player.file_loader import SettingsLoader
from adb_auto_player.models.commands import Command

from .summary_generator import SummaryGenerator


class Execute:
    """Util class for executing commands, callables, etc."""

    @staticmethod
    def command(
        command_to_execute: Command, instance: object | None = None
    ) -> Exception | None:
        """Executes the command.

        Returns:
            Exception: The exception encountered during execution, if any. Specific
                errors such as missing ADB permissions are logged with helpful messages.
            None: If the action completes successfully without raising any exceptions.
        """
        return Execute.function(
            callable_function=command_to_execute.action,
            instance=instance,
            kwargs=command_to_execute.kwargs,
        )

    @staticmethod
    def function(  # noqa: PLR0912, PLR0915
        callable_function: Callable,
        instance: object | None = None,
        kwargs: dict | None = None,
    ) -> Exception | None:
        """Execute the function with the given keyword arguments.

        Returns:
            Exception: The exception encountered during execution, if any. Specific
                errors such as missing ADB permissions are logged with helpful messages.
            None: If the action completes successfully without raising any exceptions.
        """
        if kwargs is None:
            kwargs = {}

        timeout_mins = 0
        timeout_enabled = False
        try:
            # App.toml is located in the root config dir, not the profile dir
            app_config_dir = SettingsLoader.get_app_config_dir().parent
            app_settings_path = app_config_dir / "App.toml"
            if app_settings_path.exists():
                with open(app_settings_path, "rb") as f:
                    app_settings = tomllib.load(f)
                    advanced = app_settings.get("advanced", {})
                    timeout_enabled = advanced.get("restart_stuck_task", False)
                    timeout_mins = advanced.get("restart_stuck_task_after_mins", 60)
                    if timeout_enabled:
                        timeout_mins = max(3, timeout_mins)
                    watchdog_restart_delay = advanced.get("watchdog_restart_delay", 40)
        except Exception:
            watchdog_restart_delay = 40

        # --- Watchdog Logic (Activity Based) ---
        last_activity_time = time.monotonic()

        class ActivityTrackerHandler(logging.Handler):
            def emit(self, record):
                nonlocal last_activity_time
                last_activity_time = time.monotonic()

        tracker_handler = ActivityTrackerHandler()
        logging.getLogger().addHandler(tracker_handler)

        timeout_triggered = False
        watchdog_stop_event = threading.Event()

        def watchdog_loop():
            nonlocal timeout_triggered
            while not watchdog_stop_event.is_set():
                # Check every 10 seconds
                for _ in range(10):
                    if watchdog_stop_event.is_set():
                        return
                    time.sleep(1)

                elapsed = (time.monotonic() - last_activity_time) / 60
                if elapsed > timeout_mins:
                    timeout_triggered = True
                    logging.error(
                        f"No activity detected for {timeout_mins} minutes. "
                        "Interrupting main thread."
                    )
                    _thread.interrupt_main()
                    return

        watchdog_thread = None
        if timeout_enabled and timeout_mins > 0:
            watchdog_thread = threading.Thread(target=watchdog_loop)
            watchdog_thread.daemon = True
            watchdog_thread.start()
            logging.info(
                f"Watchdog active: monitoring activity with {timeout_mins} min timeout"
            )

        try:
            while True:
                try:
                    if instance is not None:
                        # Call method on provided instance directly
                        callable_function(instance, **kwargs)
                        return None

                    sig = inspect.signature(callable_function)
                    params = list(sig.parameters.values())

                    # Determine if it's an instance method by checking the first param
                    needs_instance = (
                        params
                        and params[0].kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD,)
                        and params[0].name == "self"
                    )

                    if needs_instance:
                        # Derive class and bind instance as before
                        qual_name = cast(
                            str, getattr(callable_function, "__qualname__", None)
                        )
                        cls_name: str = qual_name.split(".")[0]
                        mod = sys.modules[callable_function.__module__]

                        orig_cls = getattr(mod, cls_name)
                        cls = None

                        # If the method belongs to a Mixin, we might need to instantiate
                        # the host Game class instead. True Mixins are just pieces of
                        # logic and don't inherit from Game Base, lacking attributes
                        # like device.
                        if "Mixin" in cls_name:
                            try:
                                # e.g. adb_auto_player.games.afk_journey.mixins.
                                # hero_scanner
                                parts = callable_function.__module__.split(".")
                                if "games" in parts:
                                    idx = parts.index("games")
                                    # Root package of the game,
                                    # e.g., adb_auto_player.games.afk_journey
                                    parent_pkg = ".".join(parts[: idx + 2])
                                    base_mod_name = f"{parent_pkg}.base"
                                    base_mod = importlib.import_module(base_mod_name)
                                    # Find the class that contains 'Base' in its name
                                    # (e.g., AFKJourneyBase)
                                    for attr_name in dir(base_mod):
                                        attr = getattr(base_mod, attr_name)
                                        if (
                                            inspect.isclass(attr)
                                            and "Base" in attr_name
                                            and attr.__module__ == base_mod_name
                                        ):
                                            if not issubclass(orig_cls, attr):
                                                cls = attr
                                            break
                            except Exception:
                                pass

                        if cls is None:
                            cls = orig_cls

                        instance = cls()

                        try:
                            callable_function(instance, **kwargs)
                        finally:
                            if hasattr(instance, "stop_stream") and callable(
                                getattr(instance, "stop_stream")
                            ):
                                instance.stop_stream()
                    else:
                        # Function doesn't expect self — call it directly
                        callable_function(**kwargs)
                    break  # Success, exit the loop
                except KeyboardInterrupt:
                    if timeout_triggered:
                        logging.warning(
                            "Task timeout triggered, restarting game and "
                            "retrying task..."
                        )
                        if instance is not None and hasattr(instance, "restart_game"):
                            try:
                                cast(Any, instance).restart_game()
                                timeout_triggered = False
                                logging.info(
                                    "Waiting %s seconds for game to restart...",
                                    watchdog_restart_delay,
                                )
                                time.sleep(watchdog_restart_delay)
                                last_activity_time = time.monotonic()
                                continue  # Retry the loop
                            except Exception as ex:
                                logging.error(f"Failed to restart game: {ex}")
                        return AutoPlayerError(
                            f"Task exceeded {timeout_mins} minutes timeout."
                        )

                    # Manual Ctrl+C
                    summary = SummaryGenerator().get_summary_message()
                    if summary is not None:
                        print(summary)
                    sys.exit(0)
                except Exception as e:
                    # java.lang.SecurityException should always be fatal
                    if timeout_enabled and "java.lang.SecurityException" not in str(e):
                        logging.warning(
                            f"Task failed with error: {e}. "
                            "Restarting game and retrying..."
                        )
                        if instance is not None and hasattr(instance, "restart_game"):
                            try:
                                cast(Any, instance).restart_game()
                                logging.info(
                                    "Waiting %s seconds for game to restart...",
                                    watchdog_restart_delay,
                                )
                                time.sleep(watchdog_restart_delay)
                                last_activity_time = time.monotonic()
                                continue  # Retry the loop
                            except Exception as ex:
                                logging.error(f"Failed to restart game: {ex}")
                        return e

                    if "java.lang.SecurityException" in str(e):
                        return GenericAdbUnrecoverableError(
                            "Missing permissions, check if your device has settings, "
                            'such as: "USB debugging (Security settings)" and '
                            "enable them."
                        )
                    return e
        finally:
            # Cleanup watchdog
            watchdog_stop_event.set()
            logging.getLogger().removeHandler(tracker_handler)
            if watchdog_thread and watchdog_thread.is_alive():
                watchdog_thread.join(timeout=1.0)
        return None

    @staticmethod
    def find_command_and_execute(
        command_name: str,
        commands: dict[str, list[Command]],
        instance: object | None = None,
    ) -> bool | Exception:
        """Helper that iterates through the command list to execute the correct one."""
        command_name_lower = command_name.lower()
        for category_commands in commands.values():
            for cmd in category_commands:
                if cmd.name.lower() == command_name_lower:
                    result = Execute.command(cmd, instance=instance)
                    return True if result is None else result
        return False
