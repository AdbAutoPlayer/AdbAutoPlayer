"""ADB Auto Player Logging Module."""

from datetime import datetime, timezone


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

    def __init__(
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
