import argparse
import json
import sys
from datetime import datetime
from typing import Any

# Color definitions (same as TerminalLogHandler)
COLORS = {
    "DEBUG": "\033[94m",  # Blue
    "INFO": "\033[92m",  # Green
    "WARNING": "\033[93m",  # Yellow
    "ERROR": "\033[91m",  # Red
    "FATAL": "\033[95m",  # Magenta
    "RESET": "\033[0m",  # Reset
}


def _format_log_message(log: dict[str, Any]) -> str:
    """Format a log message dictionary into a colored string like TerminalLogHandler."""
    level = log.get("level", "DEBUG").upper()
    timestamp = log.get("timestamp", "")
    try:
        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    except Exception:
        pass

    source_file = log.get("source_file", "unknown")
    function_name = log.get("function_name", "")
    line_number = log.get("line_number", "")

    message = log.get("message", "")

    color = COLORS.get(level, COLORS["RESET"])

    formatted = (
        f"{color}[{level}] "
        f"{timestamp} "
        f"{source_file}:{line_number} ({function_name}) - "
        f"{message}"
        f"{COLORS['RESET']}"
    )
    return formatted


def _print_logs_from_json_lines(file_path: str):
    """Read a JSON Lines (NDJSON) log file and print each entry in a formatted way."""
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            sanitized_line = line.strip()
            if not sanitized_line:
                continue
            try:
                log_entry = json.loads(sanitized_line)
                print(_format_log_message(log_entry))
                sys.stdout.flush()
            except json.JSONDecodeError as e:
                print(f"Failed to parse line: {line}\nError: {e}", file=sys.stderr)


def main():
    """Script to convert .log files into Terminal output."""
    parser = argparse.ArgumentParser(
        description="Print JSON Lines logs in terminal format."
    )
    parser.add_argument("json_file", help="Path to the JSON Lines log file")
    args = parser.parse_args()

    _print_logs_from_json_lines(args.json_file)


if __name__ == "__main__":
    main()
