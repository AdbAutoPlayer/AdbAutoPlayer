import pytest
import logging
import json
import sys
import os
import re
from unittest.mock import patch, MagicMock, call, ANY, mock_open
from datetime import datetime
from adb_auto_player.logging_setup import BaseLogHandler, JsonLogHandler, TextLogHandler, TerminalLogHandler, setup_logging, sanitize_path
from adb_auto_player.ipc import LogMessage

# Mock the ipc module and its classes as they might not be available directly
# or we want to control their behavior.
ipc_mock = MagicMock()
ipc_mock.LogLevel = MagicMock()
ipc_mock.LogLevel.DEBUG = "debug"
ipc_mock.LogLevel.INFO = "info"
ipc_mock.LogLevel.WARNING = "warning"
ipc_mock.LogLevel.ERROR = "error"
ipc_mock.LogLevel.FATAL = "fatal"

# Mock LogMessage class and its methods
mock_log_message_instance = MagicMock()
mock_log_message_instance.to_dict.return_value = {
    "level": "info",
    "message": "Sanitized test message",
    "timestamp": "dummy_timestamp",
    "source_file": "test_module.py",
    "function_name": "test_func",
    "line_number": 123
}
ipc_mock.LogMessage = MagicMock()
ipc_mock.LogMessage.create_log_message.return_value = mock_log_message_instance

# Patch sys.modules before importing the target module
modules_to_patch = {
    'adb_auto_player.ipc': ipc_mock,
}

patcher = patch.dict(sys.modules, modules_to_patch)

@pytest.fixture(scope="module", autouse=True)
def patch_ipc_dependency():
    """Apply ipc mock for the entire test module."""
    patcher.start()
    # Re-import the module *after* patching sys.modules
    global sanitize_path, BaseLogHandler, JsonLogHandler, TerminalLogHandler, TextLogHandler, setup_logging
    try:
        # Import the components to be tested
        from adb_auto_player.logging_setup import (
            sanitize_path as sp,
            BaseLogHandler as BLH,
            JsonLogHandler as JLH,
            TerminalLogHandler as TLH,
            TextLogHandler as TxLH,
            setup_logging as sl,
        )
        sanitize_path = sp
        BaseLogHandler = BLH
        JsonLogHandler = JLH
        TerminalLogHandler = TLH
        TextLogHandler = TxLH
        setup_logging = sl

    except ImportError as e:
        pytest.fail(f"Failed to import module after patching: {e}")

    yield # Run tests
    patcher.stop()

# --- Fixtures ---

@pytest.fixture
def mock_log_record():
    """Creates a mock logging.LogRecord."""
    record = MagicMock(spec=logging.LogRecord)
    record.levelno = logging.INFO
    record.levelname = "INFO"
    record.getMessage.return_value = "Original test message with path /home/user/file.txt"
    record.module = "test_module"
    record.funcName = "test_func"
    record.lineno = 123
    record.created = datetime.now().timestamp()
    record.name = "test_logger"
    return record

@pytest.fixture
def base_log_handler():
    """Provides an instance of BaseLogHandler."""
    handler = BaseLogHandler()
    return handler

@pytest.fixture
def json_log_handler():
    """Provides an instance of JsonLogHandler."""
    handler = JsonLogHandler()
    return handler

@pytest.fixture
def terminal_log_handler():
    """Provides an instance of TerminalLogHandler."""
    if TerminalLogHandler is None:
        pytest.skip("TerminalLogHandler not found during import")
    handler = TerminalLogHandler()
    return handler

@pytest.fixture
def text_log_handler():
    """Provides an instance of TextLogHandler."""
    if TextLogHandler is None:
        pytest.skip("TextLogHandler not found during import")
    handler = TextLogHandler()
    return handler

# --- Tests for sanitize_path ---

@patch('os.path.expanduser')
@patch('os.name', 'posix') # Simulate Unix-like OS
def test_sanitize_path_unix(mock_expanduser):
    """Test sanitize_path on Unix-style paths."""
    mock_expanduser.return_value = "/home/testuser"
    log_msg = "Error in file /home/testuser/project/src/main.py at line 10"
    expected = "Error in file /home/$USER/project/src/main.py at line 10"
    assert sanitize_path(log_msg) == expected

    log_msg_no_match = "Using default config /etc/app.conf"
    assert sanitize_path(log_msg_no_match) == log_msg_no_match

@patch('os.path.expanduser')
@patch('os.name', 'nt') # Simulate Windows OS
def test_sanitize_path_windows(mock_expanduser):
    """Test sanitize_path on Windows-style paths."""
    mock_expanduser.return_value = "C:\\Users\\testuser"

    log_msg_win = "Config loaded from C:\\Users\\testuser\\Documents\\config.toml"
    expected_win = "Config loaded from C:\\Users\\$env:USERNAME\\Documents\\config.toml"
    with patch('adb_auto_player.logging_setup.os.path.expanduser', return_value="C:\\Users\\testuser"):
        sanitized = sanitize_path(log_msg_win)
        assert "$env:USERNAME" in sanitized
        assert "testuser" not in sanitized
        assert sanitized.startswith("Config loaded from C:\\Users\\$env:USERNAME")

    log_msg_escaped = "Path is C:\\\\Users\\\\testuser\\\\AppData"
    expected_escaped = "Path is C:\\\\Users\\\\$env:USERNAME\\\\AppData"
    with patch('adb_auto_player.logging_setup.os.path.expanduser', return_value="C:\\Users\\testuser"):
         sanitized_escaped = sanitize_path(log_msg_escaped)
         assert "$env:USERNAME" in sanitized_escaped
         assert "testuser" not in sanitized_escaped
         assert sanitized_escaped.startswith("Path is C:\\\\Users\\\\$env:USERNAME")

    log_msg_no_match = "Using system path C:\\Windows\\System32"
    with patch('adb_auto_player.logging_setup.os.path.expanduser', return_value="C:\\Users\\testuser"):
        assert sanitize_path(log_msg_no_match) == log_msg_no_match

# --- Tests for BaseLogHandler ---

@patch("adb_auto_player.logging_setup.sanitize_path")
def test_base_log_handler_get_sanitized_message(mock_sanitize, base_log_handler, mock_log_record):
    """Test BaseLogHandler.get_sanitized_message calls sanitize_path."""
    if base_log_handler is None: pytest.skip("Handler not available")

    mock_log_record.getMessage.return_value = "Original message with /path/to/file"
    mock_sanitize.return_value = "Original message with sanitized_path"

    sanitized_msg = base_log_handler.get_sanitized_message(mock_log_record)

    mock_log_record.getMessage.assert_called_once()
    mock_sanitize.assert_called_once_with("Original message with /path/to/file")
    assert sanitized_msg == "Original message with sanitized_path"

def test_base_log_handler_get_debug_info(base_log_handler, mock_log_record):
    """Test BaseLogHandler.get_debug_info formats correctly."""
    expected = f"({mock_log_record.module}.py::{mock_log_record.funcName}::{mock_log_record.lineno})"
    debug_info = base_log_handler.get_debug_info(mock_log_record)
    assert debug_info == expected

# --- Tests for JsonLogHandler ---

@patch('json.dumps', return_value='{"json": "output"}') # Mock return value for dumps
@patch('builtins.print')
@patch('sys.stdout.flush')
def test_json_log_handler_emit(mock_flush, mock_print, mock_dumps, json_log_handler, mock_log_record):
    """Test JsonLogHandler.emit formats and prints JSON."""
    if json_log_handler is None: pytest.skip("Handler not available")

    mock_log_message_instance = MagicMock()
    mock_log_message_dict = {
        "level": "info",
        "message": "Sanitized test message",
        "timestamp": "dummy_ts",
        "source_file": "test_module.py",
        "function_name": "test_func",
        "line_number": 123
    }
    mock_log_message_instance.to_dict.return_value = mock_log_message_dict

    with patch('adb_auto_player.logging_setup.LogMessage.create_log_message', return_value=mock_log_message_instance) as mock_create_log, \
         patch.object(JsonLogHandler, 'get_sanitized_message', return_value="Sanitized test message") as mock_get_sanitized:

        mock_log_record.levelno = logging.INFO
        mock_log_record.levelname = "INFO"
        mock_log_record.pathname = "test_module.py"
        mock_log_record.funcName = "test_func"
        mock_log_record.lineno = 123
        mock_log_record.msecs = 0
        mock_log_record.created = 0

        json_log_handler.emit(mock_log_record)

        mock_get_sanitized.assert_called_once_with(mock_log_record)
        mock_create_log.assert_called_once_with(
            level=ANY,
            message="Sanitized test message",
            source_file="test_module.py",
            function_name="test_func",
            line_number=123
        )
        mock_log_message_instance.to_dict.assert_called_once()
        mock_dumps.assert_called_once_with(mock_log_message_dict)
        mock_print.assert_called_once_with('{"json": "output"}')
        mock_flush.assert_called_once()

# --- Tests for TerminalLogHandler ---

@patch('builtins.print')
@patch('sys.stdout.flush')
def test_terminal_log_handler_emit(mock_flush, mock_print, terminal_log_handler, mock_log_record):
    """Test TerminalLogHandler.emit formats and prints colored output."""
    if terminal_log_handler is None: pytest.skip("Handler not available")

    with patch.object(TerminalLogHandler, 'get_sanitized_message', return_value="Sanitized term message") as mock_get_sanitized:
        mock_log_record.msecs = 123
        mock_log_record.created = 1678886400.123
        mock_log_record.pathname = "test.py"
        mock_log_record.lineno = 42
        mock_log_record.funcName = "test_func"

        mock_log_record.levelno = logging.DEBUG
        mock_log_record.levelname = "DEBUG"
        terminal_log_handler.emit(mock_log_record)

        mock_log_record.levelno = logging.INFO
        mock_log_record.levelname = "INFO"
        terminal_log_handler.emit(mock_log_record)

        mock_log_record.levelno = logging.WARNING
        mock_log_record.levelname = "WARNING"
        terminal_log_handler.emit(mock_log_record)

        mock_log_record.levelno = logging.ERROR
        mock_log_record.levelname = "ERROR"
        terminal_log_handler.emit(mock_log_record)

        mock_log_record.levelno = logging.CRITICAL
        mock_log_record.levelname = "CRITICAL"
        terminal_log_handler.emit(mock_log_record)

        assert mock_print.call_count == 5
        info_call_args, _ = mock_print.call_args_list[1]
        assert isinstance(info_call_args[0], str)
        assert "[INFO]" in info_call_args[0]
        assert "Sanitized term message" in info_call_args[0]
        assert mock_flush.call_count == 5

# --- Tests for TextLogHandler ---

@patch('builtins.print')
@patch('sys.stdout.flush')
def test_text_log_handler_emit(mock_flush, mock_print, text_log_handler, mock_log_record):
    """Test TextLogHandler.emit formats and prints plain text."""
    if text_log_handler is None: pytest.skip("Handler not available")

    mock_log_record.msecs = 456
    mock_log_record.created = 1678886400.456
    mock_log_record.levelname = "INFO"
    mock_log_record.pathname = "test_module.py"
    mock_log_record.lineno = 101
    mock_log_record.funcName = "another_func"

    with patch.object(TextLogHandler, 'get_sanitized_message', return_value="Sanitized text message") as mock_get_sanitized:
        text_log_handler.emit(mock_log_record)

        mock_get_sanitized.assert_called_once_with(mock_log_record)
        mock_print.assert_called_once()
        printed_args, _ = mock_print.call_args
        assert isinstance(printed_args[0], str)
        assert "INFO" in printed_args[0]
        assert "Sanitized text message" in printed_args[0]
        assert "test_module.py::another_func::101" in printed_args[0]
        mock_flush.assert_called_once()

# --- Tests for setup_logging ---

root_logger = logging.getLogger()

@patch('logging.getLogger')
def test_setup_logging_sets_level(mock_get_logger):
    """Test setup_logging sets the logger level correctly."""
    if setup_logging is None:
        pytest.skip("setup_logging not found during import")

    mock_logger_instance = MagicMock(spec=logging.Logger)
    mock_logger_instance.handlers = []
    mock_get_logger.return_value = mock_logger_instance

    setup_logging(handler_type="terminal", level=logging.DEBUG)

    mock_get_logger.assert_called_with()
    mock_logger_instance.setLevel.assert_called_once_with(logging.DEBUG)

@patch('logging.getLogger', return_value=MagicMock(spec=logging.Logger))
def test_setup_logging_removes_existing_handlers(mock_get_logger):
    """Test setup_logging removes existing handlers (except for 'raw')."""
    if setup_logging is None:
        pytest.skip("setup_logging not found during import")

    mock_logger_instance = mock_get_logger.return_value
    mock_handler1 = MagicMock(spec=logging.Handler)
    mock_handler2 = MagicMock(spec=logging.Handler)
    mock_logger_instance.handlers = [mock_handler1, mock_handler2]

    setup_logging(handler_type="text", level=logging.INFO)

    mock_logger_instance.removeHandler.assert_has_calls([
        call(mock_handler1),
        call(mock_handler2)
    ], any_order=True)

@patch('logging.getLogger', return_value=MagicMock(spec=logging.Logger))
def test_setup_logging_adds_correct_handler(mock_get_logger):
    """Test setup_logging adds the correct handler instance."""
    if setup_logging is None:
        pytest.skip("setup_logging not found during import")

    mock_logger_instance = mock_get_logger.return_value
    mock_logger_instance.handlers = []

    handler_map = {
        "json": JsonLogHandler,
        "terminal": TerminalLogHandler,
        "text": TextLogHandler,
    }

    for handler_name, handler_class in handler_map.items():
        if handler_class is None:
            continue

        mock_logger_instance.reset_mock()
        mock_logger_instance.handlers = []

        with patch(f'adb_auto_player.logging_setup.{handler_class.__name__}', return_value=MagicMock(spec=handler_class)) as mock_handler_constructor:
            setup_logging(handler_type=handler_name, level=logging.INFO)

            mock_handler_constructor.assert_called_once_with()
            mock_logger_instance.addHandler.assert_called_once_with(mock_handler_constructor.return_value)

@patch('logging.getLogger', return_value=MagicMock(spec=logging.Logger))
def test_setup_logging_raw_handler_type(mock_get_logger):
    """Test setup_logging with 'raw' handler type does not remove/add handlers."""
    if setup_logging is None:
        pytest.skip("setup_logging not found during import")

    mock_logger_instance = mock_get_logger.return_value
    mock_handler = MagicMock(spec=logging.Handler)
    mock_logger_instance.handlers = [mock_handler]

    setup_logging(handler_type="raw", level=logging.INFO)

    mock_logger_instance.setLevel.assert_called_once_with(logging.INFO)
    mock_logger_instance.removeHandler.assert_not_called()
    mock_logger_instance.addHandler.assert_not_called()

@patch('logging.getLogger', return_value=MagicMock(spec=logging.Logger))
def test_setup_logging_unknown_handler_type(mock_get_logger):
    """Test setup_logging raises ValueError for unknown handler type."""
    if setup_logging is None:
        pytest.skip("setup_logging not found during import")

    mock_logger_instance = mock_get_logger.return_value
    mock_logger_instance.handlers = []

    unknown_type = "unknown_handler"
    with pytest.raises(ValueError, match=f"Unknown handler type: {unknown_type}"):
        setup_logging(handler_type=unknown_type, level=logging.INFO)

    mock_logger_instance.addHandler.assert_not_called()
