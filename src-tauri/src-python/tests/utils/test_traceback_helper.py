import logging
import sys
from unittest.mock import patch

from adb_auto_player.util.traceback_helper import (
    SourceInfo,
    TracebackHelper,
)


class TestSourceInfo:
    """Tests for SourceInfo named tuple."""

    def test_source_info_creation(self):
        """Test that SourceInfo can be created with expected attributes."""
        info = SourceInfo("test.py", "test_func", 42)
        assert info.source_file == "test.py"
        assert info.function_name == "test_func"
        assert info.line_number == 42

    def test_source_info_optional_line_number(self):
        """Test that SourceInfo can be created with None line number."""
        info = SourceInfo("test.py", "test_func", None)
        assert info.line_number is None


class TestExtractSourceInfo:
    """Tests for extract_source_info function."""

    def test_extract_source_info_defaults(self):
        """Test extraction with no exception info falls back to log record defaults."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/path/to/module.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_func",
        )

        result = TracebackHelper.extract_source_info(record)
        assert result.source_file == "module.py"
        assert result.function_name == "test_func"
        assert result.line_number == 42

    def test_extract_source_info_with_traceback(self):
        """Test extraction with valid traceback info."""
        # Create a real traceback
        try:
            raise ValueError("Test error")
        except ValueError:
            exc_type, exc_value, exc_tb = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="/path/to/module.py",
            lineno=42,
            msg="Test error",
            args=(),
            exc_info=(exc_type, exc_value, exc_tb),
            func="test_func",
        )

        result = TracebackHelper.extract_source_info(record)
        # The actual values will depend on where this test is run from
        assert result.source_file.endswith(".py")
        assert result.function_name == "test_extract_source_info_with_traceback"
        assert isinstance(result.line_number, int)

    def test_extract_source_info_with_invalid_traceback(self):
        """Test extraction falls back when traceback is invalid."""
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="/path/to/module.py",
            lineno=42,
            msg="Test error",
            args=(),
            exc_info=(
                ValueError,
                ValueError("test"),
                "not a traceback",
            ),  # invalid traceback
            func="test_func",
        )

        result = TracebackHelper.extract_source_info(record)
        assert result.source_file == "module.py"
        assert result.function_name == "test_func"
        assert result.line_number == 42

    def test_extract_source_info_with_short_exc_info(self):
        """Test extraction falls back when exc_info is too short."""
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="/path/to/module.py",
            lineno=42,
            msg="Test error",
            args=(),
            exc_info=(ValueError, ValueError("test")),  # too short
            func="test_func",
        )

        result = TracebackHelper.extract_source_info(record)
        assert result.source_file == "module.py"
        assert result.function_name == "test_func"
        assert result.line_number == 42

    def test_extract_source_info_with_empty_frame_summary(self):
        """Test extraction falls back when frame summary is empty."""
        with patch("traceback.extract_tb", return_value=[]):
            try:
                raise ValueError("Test error")
            except ValueError:
                exc_type, exc_value, exc_tb = sys.exc_info()

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="/path/to/module.py",
                lineno=42,
                msg="Test error",
                args=(),
                exc_info=(exc_type, exc_value, exc_tb),
                func="test_func",
            )

            result = TracebackHelper.extract_source_info(record)
            assert result.source_file == "module.py"
            assert result.function_name == "test_func"
            assert result.line_number == 42


class TestFormatDebugInfo:
    """Tests for format_debug_info function."""

    def test_format_debug_info_defaults(self):
        """Test formatting with default log record values."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/path/to/module.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_func",
        )

        result = TracebackHelper.format_debug_info(record)
        assert result == "(module.py::test_func::42)"

    def test_format_debug_info_with_traceback(self):
        """Test formatting with traceback-derived values."""
        try:
            raise ValueError("Test error")
        except ValueError:
            exc_type, exc_value, exc_tb = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="/path/to/module.py",
            lineno=42,
            msg="Test error",
            args=(),
            exc_info=(exc_type, exc_value, exc_tb),
            func="test_func",
        )

        result = TracebackHelper.format_debug_info(record)
        # The actual values will depend on where this test is run from
        assert result.startswith("(")
        assert "::" in result
        assert result.endswith(")")
