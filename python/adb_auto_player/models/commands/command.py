"""ADB Auto Player Command Module."""

from collections.abc import Callable
from typing import Any

from .menu_item import MenuItem


class Command:
    """Command class."""

    def __init__(
        self,
        name: str,
        action: Callable,
        kwargs: dict | None = None,
        menu_option: MenuItem | None = None,
    ) -> None:
        """Defines a CLI command / GUI Button.

        Args:
            name (str): Command name.
            action (Callable): Function that will be executed for the command.
            kwargs (dict | None): Keyword arguments for the action function.
            menu_option (MenuItem | None): GUI button options.

        Raises:
            ValueError: If name contains whitespace.
        """
        if " " in name:
            raise ValueError(f"Command name '{name}' should not contain spaces.")
        self.name: str = name
        self.action: Callable[..., Any] = action
        self.kwargs: dict[str, str] = kwargs if kwargs is not None else {}

        if menu_option is None:
            menu_option = MenuItem(
                label=name,
                display_in_gui=False,
            )

        if menu_option.args is None:
            menu_option.args = [name]

        self.menu_option: MenuItem = menu_option
