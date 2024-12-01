import logging
import eel
from logging import StreamHandler, Formatter
from typing import Any

# \033[97m White
LOG_COLORS = {
    "DEBUG": "\033[94m",  # Blue
    "INFO": "\033[92m",  # Cyan
    "WARNING": "\033[93m",  # Yellow
    "ERROR": "\033[31m",  # Red (a bit orange)
    "CRITICAL": "\033[91m",  # Red
}

RESET_COLOR = "\033[0m"  # Reset to default color


class ColoredFormatter(logging.Formatter):
    def __init__(self, fmt: str, datefmt: str | None = None) -> None:
        super().__init__(fmt, datefmt)

    def format(self, record: logging.LogRecord) -> str:
        log_color = LOG_COLORS.get(record.levelname, RESET_COLOR)

        formatted_message = super().format(record)
        return f"{log_color}{formatted_message}{RESET_COLOR}"


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


def update_logging_from_config(config: dict[str, Any]) -> None:
    logging_config = config.get("logging", {})
    log_level = logging_config.get("level", "DEBUG").upper()
    logger = logging.getLogger()
    level = getattr(logging, log_level, logging.DEBUG)
    logger.setLevel(level)
    logging.debug(f"Log level set to: {log_level}")


class FrontendHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        log_entry = self.format(record)
        if "HTTP/" in log_entry:
            return None

        if hasattr(eel, "append_to_log"):
            eel.append_to_log(log_entry)
        return None


def enable_frontend_logs() -> None:
    handler = FrontendHandler()
    formatter = Formatter(
        fmt="[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(handler)
    logging.debug("Initialized Logging FrontendHandler")
