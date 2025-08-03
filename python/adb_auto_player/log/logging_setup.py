"""ADB Auto Player Logging Setup Module."""

import logging
import sys
from datetime import datetime
from typing import ClassVar, Literal

from adb_auto_player.ipc import LogMessage
from adb_auto_player.util import (
    LogMessageFactory,
    StringHelper,
    TracebackHelper,
)

from .log_presets import LogPreset


class BaseLogHandler(logging.Handler):
    """Base log handler with common functionality."""


class TerminalLogHandler(BaseLogHandler):
    """Terminal log handler for logging to the console with colors."""

    COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[95m",  # Magenta
        "RESET": "\033[0m",  # Reset to default
    }

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log message in colored text format.

        Args:
            record (logging.LogRecord): The log record to emit.
        """
        log_level: str = record.levelname

        log_preset: LogPreset | None = getattr(record, "preset", None)

        if log_preset is not None:
            color: str = log_preset.get_terminal_color()
        else:
            color = self.COLORS.get(log_level, self.COLORS["RESET"])

        formatted_message: str = (
            f"{color}"
            f"[{log_level}] "
            f"{TracebackHelper.format_debug_info(record)} "
            f"{StringHelper.sanitize_path(record.getMessage())}"
            f"{self.COLORS['RESET']}"
        )
        print(formatted_message)
        sys.stdout.flush()


class TextLogHandler(BaseLogHandler):
    """Text log handler for logging to the console with timestamps."""

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log message in text format with timestamp.

        Args:
            record (logging.LogRecord): The log record to emit.
        """
        log_level: str = record.levelname
        timestamp: str = datetime.fromtimestamp(record.created).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        timestamp_with_ms: str = f"{timestamp}.{int(record.msecs):03d}"

        formatted_message: str = (
            f"{timestamp_with_ms} [{log_level}] "
            f"{TracebackHelper.format_debug_info(record)} "
            f"{StringHelper.sanitize_path(record.getMessage())}"
        )
        print(formatted_message)
        sys.stdout.flush()


class MemoryLogHandler(logging.Handler):
    """Log handler that stores log messages in memory for API responses."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.messages: list[LogMessage] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Store log message in memory.

        Args:
            record (logging.LogRecord): The log record to store.
        """
        preset: LogPreset | None = getattr(record, "preset", None)

        log_message: LogMessage = LogMessageFactory.create_log_message(
            record=record,
            message=StringHelper.sanitize_path(record.getMessage()),
            html_class=preset.get_html_class() if preset else None,
        )
        self.messages.append(log_message)

    def get_messages(self) -> list[LogMessage]:
        """Get all stored log messages.

        Returns:
            List[LogMessage]: All captured log messages.
        """
        return self.messages.copy()

    def clear(self) -> None:
        """Clear all stored log messages."""
        self.messages.clear()


LogHandlerType = Literal["terminal", "text", "raw"]


def setup_logging(handler_type: LogHandlerType, level: int | str) -> None:
    """Set up logging with specified handler type and level.

    Args:
        handler_type (LogHandlerType): Type of log handler to use
        level (int | str): The log level to set
    """
    logger: logging.Logger = logging.getLogger()
    logger.setLevel(level)

    if "raw" == handler_type:
        return

    for handler in logger.handlers:
        logger.removeHandler(handler)

    handler_mapping = {
        "terminal": TerminalLogHandler,
        "text": TextLogHandler,
    }

    handler_class = handler_mapping.get(handler_type)
    if handler_class:
        logger.addHandler(handler_class())
    else:
        raise ValueError(f"Unknown handler type: {handler_type}")
