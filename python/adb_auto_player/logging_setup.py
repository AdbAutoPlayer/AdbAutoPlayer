import json
import logging
import sys

from adb_auto_player.ipc.log_message import LogMessage, LogLevel


class JsonLogHandler(logging.Handler):
    def emit(self, record):
        level_mapping = {
            logging.DEBUG: LogLevel.DEBUG,
            logging.INFO: LogLevel.INFO,
            logging.WARNING: LogLevel.WARNING,
            logging.ERROR: LogLevel.ERROR,
            logging.CRITICAL: LogLevel.FATAL
        }

        log_message = LogMessage.create_log_message(level_mapping.get(record.levelno, LogLevel.DEBUG), record.getMessage())
        log_dict = log_message.to_dict()
        log_json = json.dumps(log_dict)
        print(log_json)
        sys.stdout.flush()


def setup_json_log_handler(log_level: int):
    logger = logging.getLogger()
    logger.setLevel(log_level)
    json_handler = JsonLogHandler()
    logger.addHandler(json_handler)