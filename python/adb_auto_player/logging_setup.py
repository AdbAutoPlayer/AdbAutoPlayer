import json
import logging
import sys
import os
import re

from adb_auto_player.ipc.log_message import LogMessage, LogLevel


def sanitize_path(log_message):
    """
    Sanitizes file paths in log messages by replacing the username with '<redacted>'.
    Works with both Windows and Unix-style paths.

    Args:
        log_message (str): The log message containing file paths

    Returns:
        str: The sanitized log message with usernames redacted
    """
    home_dir = os.path.expanduser("~")

    if "\\" in home_dir:  # Windows path
        username = home_dir.split("\\")[-1]
        pattern = re.escape(f"C:\\Users\\{username}")
        replacement = r"C:\\Users\\<redacted>"
    else:  # Unix path
        username = home_dir.split("/")[-1]
        pattern = f"/home/{username}"
        replacement = "/home/<redacted>"

    sanitized_message = re.sub(pattern, replacement, log_message)

    return sanitized_message


class JsonLogHandler(logging.Handler):
    def emit(self, record):
        level_mapping = {
            logging.DEBUG: LogLevel.DEBUG,
            logging.INFO: LogLevel.INFO,
            logging.WARNING: LogLevel.WARNING,
            logging.ERROR: LogLevel.ERROR,
            logging.CRITICAL: LogLevel.FATAL,
        }

        sanitized_message = sanitize_path(record.getMessage())

        log_message = LogMessage.create_log_message(
            level_mapping.get(record.levelno, LogLevel.DEBUG), sanitized_message
        )
        log_dict = log_message.to_dict()
        log_json = json.dumps(log_dict)
        print(log_json)
        sys.stdout.flush()


def setup_json_log_handler(level: int | str):
    logger = logging.getLogger()
    logger.setLevel(level)
    json_log_handler = JsonLogHandler()
    logger.addHandler(json_log_handler)


class TextLogHandler(logging.StreamHandler):
    COLORS = {
        "DEBUG": "\033[94m",  # Blue
        "INFO": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[95m",  # Magenta
        "RESET": "\033[0m",  # Reset to default
    }

    def emit(self, record):
        log_level = record.levelname
        sanitized_message = sanitize_path(record.getMessage())
        color = self.COLORS.get(log_level, self.COLORS["RESET"])
        formatted_message = (
            f"{color}[{log_level}] {sanitized_message}{self.COLORS['RESET']}"
        )
        print(formatted_message)
        sys.stdout.flush()


def setup_text_log_handler(level: int | str):
    logger = logging.getLogger()
    logger.setLevel(level)
    text_log_handler = TextLogHandler()
    logger.addHandler(text_log_handler)
