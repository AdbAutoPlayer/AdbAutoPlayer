import logging
from typing import Dict, Any, Optional, TextIO
import sys

# \033[97m White
LOG_COLORS = {
    "DEBUG": "\033[94m",  # Blue
    "INFO": "\033[96m",  # Cyan
    "WARNING": "\033[93m",  # Yellow
    "ERROR": "\033[31m",  # Red (a bit orange)
    "CRITICAL": "\033[91m",  # Red
}

RESET_COLOR = "\033[0m"  # Reset to default color


class ColoredFormatter(logging.Formatter):
    def __init__(self, fmt: str, datefmt: Optional[str] = None) -> None:
        super().__init__(fmt, datefmt)

    def format(self, record: logging.LogRecord) -> str:
        log_color = LOG_COLORS.get(record.levelname, RESET_COLOR)

        formatted_message = super().format(record)
        return f"{log_color}{formatted_message}{RESET_COLOR}"


class StreamHandler(logging.StreamHandler[TextIO]):
    def emit(self, record: logging.LogRecord) -> None:
        if record.levelname == "CRITICAL":
            record.msg = "[EXITING] " + record.msg
            super().emit(record)
            sys.exit(1)
        else:
            super().emit(record)


def setup_logging(level: int = logging.DEBUG) -> None:
    formatter = ColoredFormatter(
        fmt="[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    )

    handler = StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(level)

    logger.addHandler(handler)
    logger.propagate = False


def update_logging_from_config(config: Dict[str, Any]) -> None:
    logging_config = config.get("logging", {})
    log_level = logging_config.get("level", "DEBUG").upper()
    logger = logging.getLogger()
    level = getattr(logging, log_level, logging.DEBUG)
    logger.setLevel(level)
    logging.debug(f"Log level set to: {log_level}")
