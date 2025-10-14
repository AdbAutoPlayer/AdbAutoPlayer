import logging
from unittest.mock import patch

import pytest
from adb_auto_player.ipc import LogLevel
from adb_auto_player.util import LogMessageFactory
from adb_auto_player.util.traceback_helper import SourceInfo


class TestCreateLogMessage:
    """Test suite for create_log_message function."""

    @pytest.fixture
    def mock_source_info(self):
        return SourceInfo(
            source_file="test_file.py", function_name="test_function", line_number=42
        )

    def test_create_debug_log_message(self, mock_source_info):
        """Test creating a DEBUG level log message."""
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="/path/to/test_file.py",
            lineno=42,
            msg="Debug message",
            args=(),
            exc_info=None,
            func="test_function",
        )

        with patch(
            "adb_auto_player.util.traceback_helper.TracebackHelper.extract_source_info",
            return_value=mock_source_info,
        ):
            result = LogMessageFactory.create_log_message(record)

        assert result.level == LogLevel.DEBUG
        assert result.message == "Debug message"
        assert result.source_file == "test_file.py"
        assert result.function_name == "test_function"
        assert result.line_number == 42
        assert result.html_class is None

    def test_create_info_log_message(self, mock_source_info):
        """Test creating an INFO level log message."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/path/to/test_file.py",
            lineno=42,
            msg="Info message",
            args=(),
            exc_info=None,
            func="test_function",
        )

        with patch(
            "adb_auto_player.util.traceback_helper.TracebackHelper.extract_source_info",
            return_value=mock_source_info,
        ):
            result = LogMessageFactory.create_log_message(record)

        assert result.level == LogLevel.INFO

    def test_create_warning_log_message(self, mock_source_info):
        """Test creating a WARNING level log message."""
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="/path/to/test_file.py",
            lineno=42,
            msg="Warning message",
            args=(),
            exc_info=None,
            func="test_function",
        )

        with patch(
            "adb_auto_player.util.traceback_helper.TracebackHelper.extract_source_info",
            return_value=mock_source_info,
        ):
            result = LogMessageFactory.create_log_message(record)

        assert result.level == LogLevel.WARNING

    def test_create_error_log_message(self, mock_source_info):
        """Test creating an ERROR level log message."""
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="/path/to/test_file.py",
            lineno=42,
            msg="Error message",
            args=(),
            exc_info=None,
            func="test_function",
        )

        with patch(
            "adb_auto_player.util.traceback_helper.TracebackHelper.extract_source_info",
            return_value=mock_source_info,
        ):
            result = LogMessageFactory.create_log_message(record)

        assert result.level == LogLevel.ERROR

    def test_create_critical_log_message(self, mock_source_info):
        """Test creating a CRITICAL/FATAL level log message."""
        record = logging.LogRecord(
            name="test",
            level=logging.CRITICAL,
            pathname="/path/to/test_file.py",
            lineno=42,
            msg="Critical message",
            args=(),
            exc_info=None,
            func="test_function",
        )

        with patch(
            "adb_auto_player.util.traceback_helper.TracebackHelper.extract_source_info",
            return_value=mock_source_info,
        ):
            result = LogMessageFactory.create_log_message(record)

        assert result.level == LogLevel.FATAL

    def test_create_log_message_with_custom_message(self, mock_source_info):
        """Test creating a log message with custom message."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/path/to/test_file.py",
            lineno=42,
            msg="Original message",
            args=(),
            exc_info=None,
            func="test_function",
        )

        with patch(
            "adb_auto_player.util.traceback_helper.TracebackHelper.extract_source_info",
            return_value=mock_source_info,
        ):
            result = LogMessageFactory.create_log_message(
                record, message="Custom message"
            )

        assert result.message == "Custom message"

    def test_create_log_message_with_html_class(self, mock_source_info):
        """Test creating a log message with HTML class."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/path/to/test_file.py",
            lineno=42,
            msg="Message with class",
            args=(),
            exc_info=None,
            func="test_function",
        )

        with patch(
            "adb_auto_player.util.traceback_helper.TracebackHelper.extract_source_info",
            return_value=mock_source_info,
        ):
            result = LogMessageFactory.create_log_message(record, html_class="special")

        assert result.html_class == "special"

    def test_create_log_message_with_unknown_level(self, mock_source_info):
        """Test creating a log message with unknown log level."""
        record = logging.LogRecord(
            name="test",
            level=999,
            pathname="/path/to/test_file.py",
            lineno=42,
            msg="Unknown level message",
            args=(),
            exc_info=None,
            func="test_function",
        )

        with patch(
            "adb_auto_player.util.traceback_helper.TracebackHelper.extract_source_info",
            return_value=mock_source_info,
        ):
            result = LogMessageFactory.create_log_message(record)

        assert result.level == LogLevel.DEBUG
