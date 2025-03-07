"""ADB Auto Player Logging Setup Module."""

import json
import logging
import os
import re
import sys
from typing import ClassVar

from adb_auto_player.ipc import LogLevel, LogMessage


def sanitize_path(log_message: str) -> str:
    """Sanitizes file paths in log messages by replacing the username with '{redacted}'.

    Works with both Windows and Unix-style paths.

    Args:
        log_message (str): The log message containing file paths

    Returns:
        str: The sanitized log message with usernames redacted
    """
    home_dir: str = os.path.expanduser("~")

    if "\\" in home_dir:  # Windows path
        username: str = home_dir.split("\\")[-1]
        pattern: str = re.escape(f":\\Users\\{username}")
        replacement = r":\\Users\\{redacted}"
        log_message = re.sub(pattern, replacement, log_message)
        pattern = re.escape(f":\\\\Users\\\\{username}")
        replacement = r":\\\\Users\\\\{redacted}"
        log_message = re.sub(pattern, replacement, log_message)

    else:  # Unix path
        username = home_dir.split("/")[-1]
        pattern = f"/home/{username}"
        replacement = "/home/{redacted}"
        log_message = re.sub(pattern, replacement, log_message)

    return log_message


class JsonLogHandler(logging.Handler):
    """JSON log handler."""

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log message in JSON format.

        Args:
            record (logging.LogRecord): The log record to emit.
        """
        level_mapping: dict[int, str] = {
            logging.DEBUG: LogLevel.DEBUG,
            logging.INFO: LogLevel.INFO,
            logging.WARNING: LogLevel.WARNING,
            logging.ERROR: LogLevel.ERROR,
            logging.CRITICAL: LogLevel.FATAL,
        }

        sanitized_message: str = sanitize_path(record.getMessage())

        log_message: LogMessage = LogMessage.create_log_message(
            level=level_mapping.get(record.levelno, LogLevel.DEBUG),
            message=sanitized_message,
            source_file=record.module + ".py",
            function_name=record.funcName,
            line_number=record.lineno,
        )
        log_dict = log_message.to_dict()
        log_json: str = json.dumps(log_dict)
        print(log_json)
        sys.stdout.flush()


def setup_json_log_handler(level: int | str) -> None:
    """Sets up a JSON log handler instance.

    Args:
        level (int | str): The log level to set.
    """
    logger: logging.Logger = logging.getLogger()
    logger.setLevel(level)
    for handler in logger.handlers:
        logger.removeHandler(handler)
    json_log_handler = JsonLogHandler()
    logger.addHandler(json_log_handler)


class TextLogHandler(logging.StreamHandler):
    """Text log handler for logging to the console."""

    COLORS: ClassVar[dict[str, str]] = {
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[95m",  # Magenta
        "RESET": "\033[0m",  # Reset to default
    }

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log message in text format.

        Args:
            record (logging.LogRecord): The log record to emit.
        """
        log_level: str = record.levelname
        sanitized_message: str = sanitize_path(record.getMessage())
        color: str = self.COLORS.get(log_level, self.COLORS["RESET"])

        debug_info: str = f"({record.module}.py::{record.funcName}::{record.lineno})"
        formatted_message: str = (
            f"{color}"
            f"[{log_level}] {debug_info} {sanitized_message}{self.COLORS['RESET']}"
        )
        print(formatted_message)
        sys.stdout.flush()


def setup_text_log_handler(level: int | str) -> None:
    """Sets up a text log handler for logging to the console.

    Args:
        level (int | str): The log level to set.
    """
    logger: logging.Logger = logging.getLogger()
    logger.setLevel(level)
    for handler in logger.handlers:
        logger.removeHandler(handler)
    text_log_handler = TextLogHandler()
    logger.addHandler(text_log_handler)
