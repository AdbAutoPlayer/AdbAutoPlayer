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

    def __init__(  # noqa: PLR0913 - TODO
        self,
        level: str,
        message: str,
        timestamp: datetime,
        source_file: str | None = None,
        function_name: str | None = None,
        line_number: int | None = None,
    ) -> None:
        """Initialize LogMessage."""
        self.level = level
        self.message = message
        self.timestamp = timestamp
        self.source_file = source_file
        self.function_name = function_name
        self.line_number = line_number

    def to_dict(self):
        """Convert LogMessage to dictionary for JSON serialization."""
        return {
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp.astimezone(timezone.utc).isoformat(),
            "source_file": self.source_file,
            "function_name": self.function_name,
            "line_number": self.line_number,
        }

    @classmethod
    def create_log_message(
        cls,
        level: str,
        message: str,
        source_file: str | None = None,
        function_name: str | None = None,
        line_number: int | None = None,
    ) -> "LogMessage":
        """Create a new LogMessage."""
        return cls(
            level=level,
            message=message,
            timestamp=datetime.now(),
            source_file=source_file,
            function_name=function_name,
            line_number=line_number,
        )
