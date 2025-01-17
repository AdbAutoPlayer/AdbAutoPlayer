from datetime import datetime, timezone


class LogLevel:
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class LogMessage:
    def __init__(
        self,
        level: str,
        message: str,
        timestamp: datetime,
        source_file: str | None = None,
        line_number: int | None = None,
    ):
        self.level = level
        self.message = message
        self.timestamp = timestamp
        self.source_file = source_file
        self.line_number = line_number

    def to_dict(self):
        """Convert LogMessage to dictionary for JSON serialization."""
        return {
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp.astimezone(timezone.utc).isoformat(),
            "source_file": self.source_file,
            "line_number": self.line_number,
        }

    @classmethod
    def create_log_message(cls, level: str, message: str):
        return cls(level, message, datetime.now())
