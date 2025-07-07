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

    def to_dict(self):
        """Convert to dict for JSON serialization."""
        return {
            "label": self.label,
            "args": self.args,
            "translated": self.translated,
            "category": self.category,
            "tooltip": self.tooltip,
        }
