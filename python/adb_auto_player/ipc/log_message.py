"""ADB Auto Player Logging Module."""

import logging
from datetime import datetime, timezone

from adb_auto_player.util.traceback_helper import extract_source_info


class LogLevel:
    """Logging levels."""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class LogMessage:
    """Log message class."""

    def __init__(  # noqa: PLR0913 - TODO
        self,
        level: str,
        message: str,
        timestamp: datetime,
        source_file: str | None = None,
        function_name: str | None = None,
        line_number: int | None = None,
        html_class: str | None = None,
    ) -> None:
        """Initialize LogMessage."""
        self.level = level
        self.message = message
        self.timestamp = timestamp
        self.source_file = source_file
        self.function_name = function_name
        self.line_number = line_number
        self.html_class = html_class

    def to_dict(self):
        """Convert LogMessage to dictionary for JSON serialization."""
        return {
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp.astimezone(timezone.utc).isoformat(),
            "source_file": self.source_file,
            "function_name": self.function_name,
            "line_number": self.line_number,
            "html_class": self.html_class,
        }

    @classmethod
    def create_log_message(
        cls,
        record: logging.LogRecord,
        message: str | None = None,
        html_class: str | None = None,
    ) -> "LogMessage":
        """Create a new LogMessage."""
        level_mapping: dict[int, str] = {
            logging.DEBUG: LogLevel.DEBUG,
            logging.INFO: LogLevel.INFO,
            logging.WARNING: LogLevel.WARNING,
            logging.ERROR: LogLevel.ERROR,
            logging.CRITICAL: LogLevel.FATAL,
        }

        source_info = extract_source_info(record)
        return cls(
            level=level_mapping.get(record.levelno, LogLevel.DEBUG),
            message=message if message else record.getMessage(),
            timestamp=datetime.now(),
            source_file=source_info.source_file,
            function_name=source_info.function_name,
            line_number=source_info.line_number,
            html_class=html_class,
        )
