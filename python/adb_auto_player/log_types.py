"""Log Types for logging presets (color, ...)."""

from enum import Enum, auto


class LogType(Enum):
    """Enum representing different types of log events in the system."""

    DEFEAT = auto()

    def get_terminal_color(self) -> str:
        """Get the terminal color."""
        colors = {
            LogType.DEFEAT: "\033[91m",  # Red
            # Add other LogTypes with their colors here
        }
        if self not in colors:
            raise ValueError(f"No color defined for LogType {self.name}")
        return colors[self]

    def get_gui_color(self) -> str:
        """Get the GUI color."""
        colors = {LogType.DEFEAT: "text-error-200"}
        if self not in colors:
            raise ValueError(f"No color defined for LogType {self.name}")
        return colors[self]
