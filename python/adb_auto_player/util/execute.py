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

import inspect
import logging
import sys
from collections.abc import Callable

from adb_auto_player.exceptions import GenericAdbError, GenericAdbUnrecoverableError
from adb_auto_player.models.commands import Command

from .summary_generator import SummaryGenerator


class Execute:
    """Util class for executing commands, callables, etc."""

    @staticmethod
    def command(command_to_execute: Command) -> Exception | None:
        """Executes the command.

        Returns:
            Exception: The exception encountered during execution, if any. Specific
                errors such as missing ADB permissions are logged with helpful messages.
            None: If the action completes successfully without raising any exceptions.
        """
        return Execute.function(
            callable_function=command_to_execute.action,
            kwargs=command_to_execute.kwargs,
        )

    @staticmethod
    def function(
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
                cls_name = callable_function.__qualname__.split(".")[0]
                mod = sys.modules[callable_function.__module__]
                cls = getattr(mod, cls_name)
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
        except KeyboardInterrupt:
            summary = SummaryGenerator().get_summary_message()
            if summary is not None:
                print(summary)
            sys.exit(0)
        except (GenericAdbError, GenericAdbUnrecoverableError) as e:
            if "java.lang.SecurityException" in str(e):
                logging.error(
                    "Missing permissions, check if your device has settings, such as: "
                    '"USB debugging (Security settings)" and enable them.'
                )
            else:
                logging.error(f"{e}", exc_info=True)
            return e
        except Exception as e:
            logging.error(f"{e}", exc_info=True)
            return e
        return None
