"""Logging presets (color, ...)."""

from enum import Enum, auto


class LogPreset(Enum):
    """Enum representing different types of log events in the system."""

    DEFEAT = auto()
    NOT_AVAILABLE = auto()

    def get_terminal_color(self) -> str:
        """Get the terminal color."""
        colors = {
            LogPreset.DEFEAT: "\033[91m",  # Red
            LogPreset.NOT_AVAILABLE: "\033[90m",  # Bright Black
            # Add other presets with their colors here
        }
        if self not in colors:
            raise ValueError(f"No color defined for LogPreset {self.name}")
        return colors[self]

    def get_html_class(self) -> str | None:
        """Get the HTML class name for GUI."""
        html_classes = {
            LogPreset.NOT_AVAILABLE: "text-tertiary-200",
        }
        if self not in html_classes:
            return None
        return html_classes[self]
