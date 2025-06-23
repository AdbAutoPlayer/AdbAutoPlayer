"""Menu Item."""

from dataclasses import dataclass


@dataclass
class MenuItem:
    """Menu Item."""

    label: str
    display_in_gui: bool = True
    args: list[str] | None = None
    category: str | None = None
    tooltip: str | None = None
