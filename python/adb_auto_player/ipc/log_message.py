"""ADB Auto Player Logging Module."""

from datetime import datetime, timezone

from pydantic import BaseModel


class LogLevel:
    """Logging levels."""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class LogMessage(BaseModel):
    """Log message class."""

    level: str
    message: str
    timestamp: datetime
    source_file: str | None = None
    function_name: str | None = None
    line_number: int | None = None
    html_class: str | None = None

    def to_dict(self):
        """Convert LogMessage to dictionary for JSON serialization."""
        return {
            "level": self.level,
            "message": self.message,
            "timestamp": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[
                :-3
            ]
            + "Z",
            "source_file": self.source_file,
            "function_name": self.function_name,
            "line_number": self.line_number,
            "html_class": self.html_class,
        }
