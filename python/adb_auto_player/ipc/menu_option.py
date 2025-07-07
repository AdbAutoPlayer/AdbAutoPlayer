"""Menu Option."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MenuOption:
    """Menu Option used by the GUI."""

    label: str
    args: list[str]
    translated: bool = False
    category: str | None = None
    tooltip: str | None = None
