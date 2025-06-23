import logging
from unittest.mock import patch

import pytest
from adb_auto_player.ipc import LogLevel
from adb_auto_player.util import create_log_message
from adb_auto_player.util.traceback_helper import SourceInfo


# Mock classes for testing
class MockLogRecord:
    def __init__(self, levelno, msg, pathname, func, lineno):
        self.levelno = levelno
        self.msg = msg
        self.pathname = pathname
        self.funcName = func
        self.lineno = lineno
        self.module = "test_file"
        self.exc_info = None

    def getMessage(self):  # noqa: N802
        return self.msg


class TestCreateLogMessage:
    """Test suite for create_log_message function."""

    @pytest.fixture
    def mock_source_info(self):
        return SourceInfo(
            source_file="test_file.py", function_name="test_function", line_number=42
        )

    def test_create_debug_log_message(self, mock_source_info):
        """Test creating a DEBUG level log message."""
        record = MockLogRecord(
            levelno=logging.DEBUG,
            msg="Debug message",
            pathname="/path/to/test_file.py",
            func="test_function",
            lineno=42,
        )

        with patch(
            "adb_auto_player.util.traceback_helper.extract_source_info",
            return_value=mock_source_info,
        ):
            result = create_log_message(record)

        assert result.level == LogLevel.DEBUG
        assert result.message == "Debug message"
        assert result.source_file == "test_file.py"
        assert result.function_name == "test_function"
        assert result.line_number == 42
        assert result.html_class is None

    def test_create_info_log_message(self, mock_source_info):
        """Test creating an INFO level log message."""
        record = MockLogRecord(
            levelno=logging.INFO,
            msg="Info message",
            pathname="/path/to/test_file.py",
            func="test_function",
            lineno=42,
        )

        with patch(
            "adb_auto_player.util.traceback_helper.extract_source_info",
            return_value=mock_source_info,
        ):
            result = create_log_message(record)

        assert result.level == LogLevel.INFO

    def test_create_warning_log_message(self, mock_source_info):
        """Test creating a WARNING level log message."""
        record = MockLogRecord(
            levelno=logging.WARNING,
            msg="Warning message",
            pathname="/path/to/test_file.py",
            func="test_function",
            lineno=42,
        )

        with patch(
            "adb_auto_player.util.traceback_helper.extract_source_info",
            return_value=mock_source_info,
        ):
            result = create_log_message(record)

        assert result.level == LogLevel.WARNING

    def test_create_error_log_message(self, mock_source_info):
        """Test creating an ERROR level log message."""
        record = MockLogRecord(
            levelno=logging.ERROR,
            msg="Error message",
            pathname="/path/to/test_file.py",
            func="test_function",
            lineno=42,
        )

        with patch(
            "adb_auto_player.util.traceback_helper.extract_source_info",
            return_value=mock_source_info,
        ):
            result = create_log_message(record)

        assert result.level == LogLevel.ERROR

    def test_create_critical_log_message(self, mock_source_info):
        """Test creating a CRITICAL/FATAL level log message."""
        record = MockLogRecord(
            levelno=logging.CRITICAL,
            msg="Critical message",
            pathname="/path/to/test_file.py",
            func="test_function",
            lineno=42,
        )

        with patch(
            "adb_auto_player.util.traceback_helper.extract_source_info",
            return_value=mock_source_info,
        ):
            result = create_log_message(record)

        assert result.level == LogLevel.FATAL

    def test_create_log_message_with_custom_message(self, mock_source_info):
        """Test creating a log message with custom message."""
        record = MockLogRecord(
            levelno=logging.INFO,
            msg="Original message",
            pathname="/path/to/test_file.py",
            func="test_function",
            lineno=42,
        )

        with patch(
            "adb_auto_player.util.traceback_helper.extract_source_info",
            return_value=mock_source_info,
        ):
            result = create_log_message(record, message="Custom message")

        assert result.message == "Custom message"

    def test_create_log_message_with_html_class(self, mock_source_info):
        """Test creating a log message with HTML class."""
        record = MockLogRecord(
            levelno=logging.INFO,
            msg="Message with class",
            pathname="/path/to/test_file.py",
            func="test_function",
            lineno=42,
        )

        with patch(
            "adb_auto_player.util.traceback_helper.extract_source_info",
            return_value=mock_source_info,
        ):
            result = create_log_message(record, html_class="special")

        assert result.html_class == "special"

    def test_create_log_message_with_unknown_level(self, mock_source_info):
        """Test creating a log message with unknown log level."""
        record = MockLogRecord(
            levelno=999,  # Unknown level
            msg="Unknown level message",
            pathname="/path/to/test_file.py",
            func="test_function",
            lineno=42,
        )

        with patch(
            "adb_auto_player.util.traceback_helper.extract_source_info",
            return_value=mock_source_info,
        ):
            result = create_log_message(record)

        assert result.level == LogLevel.DEBUG
