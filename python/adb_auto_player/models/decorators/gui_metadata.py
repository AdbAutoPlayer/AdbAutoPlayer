"""GUIMetadata."""

from dataclasses import dataclass
from enum import StrEnum


@dataclass
class GUIMetadata:
    """Metadata used to describe how a command should appear in the GUI.

    Attributes:
        label (str): Display name for the command in the menu.
        category (str | StrEnum): Category grouping for UI organization.
        tooltip (str): Help text shown when hovering over the command.
            This also doubles as CLI Command description.
    """

    label: str
    category: str | StrEnum | None = None
    tooltip: str | None = None
