"""ADB Auto Player Command Module."""

from collections.abc import Callable
from typing import Any

from adb_auto_player.ipc import MenuOption


class Command:
    """Command class."""

    def __init__(
        self,
        name: str,
        action: Callable,
        kwargs: dict | None = None,
        menu_option: MenuOption | None = None,
    ) -> None:
        """Defines a CLI command / GUI Button.

        Args:
            name (str): Command name.
            action (Callable): Function that will be executed for the command.
            kwargs (dict | None): Keyword arguments for the action function.
            menu_option (MenuOption | None): GUI button options.

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

    def run(self) -> None:
        """Execute the action with the given keyword arguments."""
        self.action(**self.kwargs)
