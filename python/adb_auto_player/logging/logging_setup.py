"""ADB Auto Player Logging Setup Module."""

import json
import logging
import os
import re
import sys
from datetime import datetime
from typing import ClassVar, Literal

from adb_auto_player.ipc import LogMessage
from adb_auto_player.logging import LogPreset
from adb_auto_player.util import SummaryGenerator, create_log_message, format_debug_info


def sanitize_path(log_message: str) -> str:
    """Replaces the username in file paths with $USER or $env:USERNAME.

    Works with both Windows and Unix-style paths.

    Args:
        log_message (str): The log message containing file paths

    Returns:
        str: The sanitized log message with environment variable placeholders
    """
    home_dir: str = os.path.expanduser("~")

    if "\\" in home_dir:  # Windows path
        username: str = home_dir.split("\\")[-1]
        pattern: str = re.escape(f":\\Users\\{username}")
        replacement = r":\\Users\\$env:USERNAME"
        log_message = re.sub(pattern, replacement, log_message)
        pattern = re.escape(f":\\\\Users\\\\{username}")
        replacement = r":\\\\Users\\\\$env:USERNAME"
        log_message = re.sub(pattern, replacement, log_message)

    else:  # Unix path
        username = home_dir.split("/")[-1]
        pattern = f"/home/{username}"
        replacement = "/home/$USER"
        log_message = re.sub(pattern, replacement, log_message)

    return log_message


class BaseLogHandler(logging.Handler):
    """Base log handler with common functionality."""

    def get_sanitized_message(self, record: logging.LogRecord) -> str:
        """Get sanitized log message.

        Args:
            record (logging.LogRecord): The log record

        Returns:
            str: Sanitized log message
        """
        return sanitize_path(record.getMessage())


class JsonLogHandler(BaseLogHandler):
    """JSON log handler this is used for IPC between CLI and GUI."""

    def __init__(self, *args, **kwargs):
        """Initialize JsonLogHandler.

        Lets the SummaryGenerator know that it needs to start sending data to the GUI.
        """
        super().__init__(*args, **kwargs)
        SummaryGenerator.set_json_handler_present()

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log message in JSON format.

        Args:
            record (logging.LogRecord): The log record to emit.
        """
        preset: LogPreset | None = getattr(record, "preset", None)

        log_message: LogMessage = create_log_message(
            record=record,
            message=self.get_sanitized_message(record),
            html_class=preset.get_html_class() if preset else None,
        )
        log_dict = log_message.to_dict()
        log_json: str = json.dumps(log_dict)
        print(log_json)
        sys.stdout.flush()


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
            f"{format_debug_info(record)} {self.get_sanitized_message(record)}"
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
            f"{timestamp_with_ms} [{log_level}] {format_debug_info(record)} "
            f"{self.get_sanitized_message(record)}"
        )
        print(formatted_message)
        sys.stdout.flush()


LogHandlerType = Literal["json", "terminal", "text", "raw"]


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
        "json": JsonLogHandler,
        "terminal": TerminalLogHandler,
        "text": TextLogHandler,
    }

    handler_class = handler_mapping.get(handler_type)
    if handler_class:
        logger.addHandler(handler_class())
    else:
        raise ValueError(f"Unknown handler type: {handler_type}")
