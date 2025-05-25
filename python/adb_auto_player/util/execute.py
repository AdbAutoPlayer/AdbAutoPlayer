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

from adb_auto_player.exceptions import GenericAdbError


def execute(
    function: Callable,
    instance: object | None = None,
    kwargs: dict | None = None,
) -> Exception | None:
    """Execute the function with the given keyword arguments.

    Returns:
        Exception: The exception encountered during execution, if any. Specific
            errors such as missing tADB permissions are logged with helpful messages.
        None: If the action completes successfully without raising any exceptions.
    """
    if kwargs is None:
        kwargs = {}

    try:
        if instance is not None:
            # Call method on provided instance directly
            function(instance, **kwargs)
            return None

        sig = inspect.signature(function)
        params = list(sig.parameters.values())

        # Determine if it's an instance method by checking the first param
        needs_instance = (
            params
            and params[0].kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD,)
            and params[0].name == "self"
        )

        if needs_instance:
            # Derive class and bind instance as before
            cls_name = function.__qualname__.split(".")[0]
            mod = sys.modules[function.__module__]
            cls = getattr(mod, cls_name)
            instance = cls()
            function(instance, **kwargs)
        else:
            # Function doesn't expect self — call it directly
            function(**kwargs)
    except GenericAdbError as e:
        if "java.lang.SecurityException" in str(e):
            logging.error(
                "Missing permissions, check if your device has the setting: "
                '"USB debugging (Security settings)" and enable it.'
            )
        return e
    except Exception as e:
        logging.error(f"{e}")
        return e
    return None
