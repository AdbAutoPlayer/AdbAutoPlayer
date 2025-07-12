"""Menu Option."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MenuOption:
    """Menu Option used by the GUI."""

    label: str
    args: list[str]
    custom_label: str | None = None
    category: str | None = None
    tooltip: str | None = None

    def to_dict(self):
        """Convert to dict for JSON serialization."""
        return {
            "label": self.label,
            "args": self.args,
            "custom_label": self.custom_label,
            "category": self.category,
            "tooltip": self.tooltip,
        }
