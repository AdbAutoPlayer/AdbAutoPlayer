"""ADB Auto Player Command Module."""

import logging
from collections.abc import Callable
from typing import Any

from adb_auto_player.ipc import MenuOption

from .exceptions import GenericAdbError


class Command:
    """Command class."""

    def __init__(
        self,
        name: str,
        action: Callable,
        kwargs: dict | None = None,
        menu_option: MenuOption | None = None,
        allow_in_my_custom_routine: bool = True,
    ) -> None:
        """Defines a CLI command / GUI Button.

        Args:
            name (str): Command name.
            action (Callable): Function that will be executed for the command.
            kwargs (dict | None): Keyword arguments for the action function.
            menu_option (MenuOption | None): GUI button options.
            allow_in_my_custom_routine (bool): Allow to be called in custom routine.

        Raises:
            ValueError: If name contains whitespace.
        """
        if " " in name:
            raise ValueError(f"Command name '{name}' should not contain spaces.")
        self.name: str = name
        self.action: Callable[..., Any] = action
        self.kwargs: dict[str, str] = kwargs if kwargs is not None else {}

        if menu_option is None:
            menu_option = MenuOption(
                label=name,
            )

        if menu_option.args is None:
            menu_option.args = [name]

        self.menu_option: MenuOption = menu_option
        self.allow_in_my_custom_routine: bool = allow_in_my_custom_routine

    def run(self) -> Exception | None:
        """Execute the action with the given keyword arguments.

        Returns:
            Exception: The exception encountered during execution, if any. Specific
                errors such as missing ADB permissions are logged with helpful messages.
            None: If the action completes successfully without raising any exceptions.
        """
        try:
            self.action(**self.kwargs)
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
