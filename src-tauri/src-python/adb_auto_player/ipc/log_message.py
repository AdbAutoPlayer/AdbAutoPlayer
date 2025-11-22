"""ADB Auto Player Logging Module."""

from datetime import datetime

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
    profile_index: int | None = None
