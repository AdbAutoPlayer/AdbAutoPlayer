"""Traceback Helper Module for ADB Auto Player Logging."""

import logging
import os
import traceback
from traceback import StackSummary
from types import TracebackType
from typing import NamedTuple

EXC_INFO_TUPLE_SIZE = 3
EXC_INFO_TRACEBACK_INDEX = 2


class SourceInfo(NamedTuple):
    """Container for source code information."""

    source_file: str
    function_name: str
    line_number: int | None


def extract_source_info(record: logging.LogRecord) -> SourceInfo:
    """Extract source information from a log record, with traceback override.

    This function safely extracts source information, falling back to log record
    defaults if traceback information is not available or fails to parse.

    Args:
        record (logging.LogRecord): The log record to extract information from

    Returns:
        SourceInfo: Named tuple containing source_file, function_name, and line_number
    """
    # Default values from the log record
    default_source_file = f"{record.module}.py"
    default_function_name = record.funcName
    default_line_number = record.lineno

    # Try to get traceback information if exception info exists
    if (
        record.exc_info
        and len(record.exc_info) >= EXC_INFO_TUPLE_SIZE
        and record.exc_info[EXC_INFO_TRACEBACK_INDEX] is not None
    ):
        try:
            frame_summary: StackSummary | None = None

            tb_candidate = record.exc_info[EXC_INFO_TRACEBACK_INDEX]
            # Type guard: ensure it's actually a TracebackType
            if isinstance(tb_candidate, TracebackType):
                frame_summary = traceback.extract_tb(tb_candidate)

            # Safely get the last frame if it exists
            if frame_summary and len(frame_summary) > 0:
                last_frame = frame_summary[-1]
                return SourceInfo(
                    source_file=os.path.basename(last_frame.filename),
                    function_name=last_frame.name,
                    line_number=last_frame.lineno,
                )
        except (IndexError, AttributeError, TypeError):
            # If anything goes wrong with traceback extraction, fall back to defaults
            pass

    # Return default values from the log record
    return SourceInfo(
        source_file=default_source_file,
        function_name=default_function_name,
        line_number=default_line_number,
    )


def format_debug_info(record: logging.LogRecord) -> str:
    """Format debug information string from log record.

    Args:
        record (logging.LogRecord): The log record

    Returns:
        str: Formatted debug information in the format (filename::function::line)
    """
    source_info = extract_source_info(record)
    return (
        f"({source_info.source_file}::{source_info.function_name}::"
        f"{source_info.line_number})"
    )
