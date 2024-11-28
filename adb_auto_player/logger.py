import logging
import sys
from typing import NoReturn


def critical_and_exit(msg: str, exit_code: int = 1) -> NoReturn:
    logging.critical("[EXITING] " + msg)
    sys.exit(exit_code)


def error(msg: str) -> None:
    logging.error(msg)


def warning(msg: str) -> None:
    logging.warning(msg)


def info(msg: str) -> None:
    logging.info(msg)


def debug(msg: str) -> None:
    logging.debug(msg)
