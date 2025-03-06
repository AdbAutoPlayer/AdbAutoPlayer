"""ADB Auto Player Command Module."""

from collections.abc import Callable
from typing import Any


class Command:
    """Command class."""

    def __init__(
        self,
        name: str,
        action: Callable,
        kwargs: dict | None = None,
        gui_label: str | None = None,
    ) -> None:
        """Defines a CLI command / GUI Button.

        Args:
            name (str): Command name.
            action (Callable): Function that will be executed for the command.
            kwargs (dict | None): Keyword arguments for the action function.
            gui_label (str | None): GUI button label.

        Raises:
            ValueError: If name contains whitespace.
        """
        if " " in name:
            raise ValueError(f"Command name '{name}' should not contain spaces.")
        self.name: str = name
        self.action: Callable[..., Any] = action
        self.kwargs: dict[str, str] = kwargs if kwargs is not None else {}
        self.gui_label: str = gui_label if gui_label is not None else name

    def run(self) -> None:
        """Execute the action with the given keyword arguments."""
        self.action(**self.kwargs)
