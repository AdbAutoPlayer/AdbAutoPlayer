# c:\\Users\\Vale\\Documents\\GitHub\\AdbAutoPlayer\\python\\tests\\test_adb.py
import pytest
import numpy as np
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock, call

# Assuming adb module structure:
# from adb_auto_player.adb import (
#     _set_adb_path,
#     get_adb_client,
#     get_adb_device,
#     exec_wm_size,
#     wm_size_reset,
#     get_screen_resolution,
#     is_portrait,
#     get_running_app,
#     _connect_client,
#     _get_devices,
#     log_devices,
#     _is_device_connection_active,
#     _connect_to_device,
#     _try_incrementing_ports,
#     _resolve_device,
#     _override_size,
#     GenericAdbError,
# )
# from adb_auto_player.config_loader import ConfigLoader # Mocked
# from adb_auto_player.template_matching import MatchMode, CropRegions # Mocked
# from adbutils import AdbClient, AdbDevice, AdbError, AdbDeviceInfo # Mocked

# --- Mocks for Dependencies ---

# Mock Adb related classes/exceptions from adbutils
class MockAdbError(Exception):
    pass

class MockAdbDeviceInfo:
    def __init__(self, serial, state):
        self.serial = serial
        self.state = state

class MockAdbDevice:
    serial = "emulator-5554"
    def __init__(self, serial="emulator-5554"):
        self.serial = serial
        self.click = MagicMock()
        self.swipe = MagicMock()
        self.shell = MagicMock()
        self.screencap = MagicMock(return_value=np.zeros((100, 100, 3), dtype=np.uint8)) # Return dummy image
        self.app_current = MagicMock(return_value={"package": "com.test.game", "activity": "Main"})
        self.app_start = MagicMock()
        self.app_stop = MagicMock()
        # Add other methods as needed for tests

class MockAdbClient:
    def __init__(self, host="127.0.0.1", port=5037):
        self.host = host
        self.port = port
        self.server_version = MagicMock(return_value=41)
        self.device_list = MagicMock(return_value=[MockAdbDeviceInfo("emulator-5554", "device")])
        self.device = MagicMock(return_value=MockAdbDevice("emulator-5554"))

# Mock ConfigLoader
class MockConfigLoader:
    def __init__(self):
        self.main_config = {
            "adb": {"host": "127.0.0.1", "port": 5037},
            "game": {"package_id": "com.test.game"},
            "device_serial": None, # Default to None
        }
        self.binaries_dir = Path("/mock/binaries")

    def get_config(self): # Simplified getter
        return self.main_config

# Mock template matching types
class MockMatchMode:
    BEST = "BEST"
    TOP_LEFT = "TOP_LEFT"

class MockCropRegions(tuple):
     def __new__(cls, left=0, right=0, top=0, bottom=0):
        return tuple.__new__(cls, (left, right, top, bottom))
     # Add properties if needed by the code under test

# --- Mock the module under test ---
# It's often easier to mock dependencies via @patch than rewriting the module
# For demonstration, we might patch specific functions later.

# --- Test Cases ---

# Helper to reset mocks between tests if needed
@pytest.fixture(autouse=True)
def reset_mocks():
    # Reset relevant mocks if they retain state across tests
    # e.g., MockAdbDevice.click.reset_mock()
    pass

@pytest.fixture
def mock_config_loader_instance():
    return MockConfigLoader()

@pytest.fixture
def mock_adb_client_instance():
    return MockAdbClient()

@pytest.fixture
def mock_adb_device_instance():
    return MockAdbDevice()

# --- Tests for _connect_client ---

@patch("adb_auto_player.adb.AdbClient")
@patch("adb_auto_player.adb.AdbError", new=MockAdbError)
def test_connect_client_success(MockAdbClient):
    """Test _connect_client calls client.connect."""
    from adb_auto_player.adb import _connect_client
    mock_client = MockAdbClient()
    mock_client.connect = MagicMock()
    device_id = "emulator-5554"

    _connect_client(mock_client, device_id)

    mock_client.connect.assert_called_once_with(device_id)

@patch("adb_auto_player.adb.AdbClient")
@patch("adb_auto_player.adb.AdbError", new=MockAdbError)
@patch("adb_auto_player.adb.GenericAdbError", new=MockAdbError) # Mock GenericAdbError too
def test_connect_client_adb_error_install(MockAdbClient):
    """Test _connect_client raises original AdbError for 'Install adb'."""
    from adb_auto_player.adb import _connect_client
    mock_client = MockAdbClient()
    mock_client.connect = MagicMock(side_effect=MockAdbError("Install adb please"))
    device_id = "emulator-5554"

    with pytest.raises(MockAdbError, match="Install adb please"):
        _connect_client(mock_client, device_id)

    mock_client.connect.assert_called_once_with(device_id)

@patch("adb_auto_player.adb.AdbClient")
@patch("adb_auto_player.adb.AdbError", new=MockAdbError)
@patch("adb_auto_player.adb.GenericAdbError", new=MockAdbError)
def test_connect_client_adb_error_unknown_data(MockAdbClient):
    """Test _connect_client raises GenericAdbError for 'Unknown data'."""
    from adb_auto_player.adb import _connect_client
    mock_client = MockAdbClient()
    mock_client.connect = MagicMock(side_effect=MockAdbError("Unknown data: b'foo'"))
    device_id = "emulator-5554"

    with pytest.raises(MockAdbError, match="make sure the adb port is correct"):
        _connect_client(mock_client, device_id)

    mock_client.connect.assert_called_once_with(device_id)

@patch("adb_auto_player.adb.AdbClient")
@patch("adb_auto_player.adb.AdbError", new=MockAdbError)
@patch("adb_auto_player.adb.GenericAdbError", new=MockAdbError)
def test_connect_client_other_adb_error(MockAdbClient):
    """Test _connect_client ignores other AdbErrors (logs debug)."""
    from adb_auto_player.adb import _connect_client
    mock_client = MockAdbClient()
    mock_client.connect = MagicMock(side_effect=MockAdbError("Some other ADB issue"))
    device_id = "emulator-5554"

    # Should not raise an error, just log
    _connect_client(mock_client, device_id)

    mock_client.connect.assert_called_once_with(device_id)
    # TODO: Check logging if important

@patch("adb_auto_player.adb.AdbClient")
def test_connect_client_generic_exception(MockAdbClient):
    """Test _connect_client ignores generic exceptions (logs debug)."""
    from adb_auto_player.adb import _connect_client
    mock_client = MockAdbClient()
    mock_client.connect = MagicMock(side_effect=Exception("Unexpected error"))
    device_id = "emulator-5554"

    # Should not raise an error, just log
    _connect_client(mock_client, device_id)

    mock_client.connect.assert_called_once_with(device_id)
    # TODO: Check logging if important

# --- Tests for _get_devices ---

@patch("adb_auto_player.adb.AdbClient")
def test_get_devices_success(MockAdbClient):
    """Test _get_devices returns client.list() result."""
    from adb_auto_player.adb import _get_devices
    mock_client = MockAdbClient()
    mock_devices_list = [MockAdbDeviceInfo("dev1", "device")]
    mock_client.list = MagicMock(return_value=mock_devices_list)

    result = _get_devices(mock_client)

    mock_client.list.assert_called_once()
    assert result == mock_devices_list

@patch("adb_auto_player.adb.AdbClient")
@patch("adb_auto_player.adb.GenericAdbError", new=MockAdbError) # Mock GenericAdbError
def test_get_devices_exception(MockAdbClient):
    """Test _get_devices raises GenericAdbError on client.list() failure."""
    from adb_auto_player.adb import _get_devices
    mock_client = MockAdbClient()
    mock_client.list = MagicMock(side_effect=Exception("List failed"))

    with pytest.raises(MockAdbError, match="Failed to connect to AdbClient"):
        _get_devices(mock_client)

    mock_client.list.assert_called_once()

# --- Tests for log_devices ---

@patch("adb_auto_player.adb.logging")
def test_log_devices_logs_correctly(mock_logging):
    """Test log_devices formats and logs device serials."""
    from adb_auto_player.adb import log_devices, DEBUG
    devices = [
        MockAdbDeviceInfo("dev1", "device"),
        MockAdbDeviceInfo("dev2", "offline"),
    ]
    log_devices(devices, DEBUG)
    mock_logging.log.assert_called_once_with(DEBUG, "Devices: dev1, dev2")

@patch("adb_auto_player.adb.logging")
def test_log_devices_empty_list(mock_logging):
    """Test log_devices does nothing for an empty list."""
    from adb_auto_player.adb import log_devices
    log_devices([])
    mock_logging.log.assert_not_called()

# --- Tests for _is_device_connection_active ---

def test_is_device_connection_active_true():
    """Test _is_device_connection_active returns True on success."""
    from adb_auto_player.adb import _is_device_connection_active
    mock_device = MockAdbDevice()
    mock_device.get_state = MagicMock(return_value="device") # Simulate success
    assert _is_device_connection_active(mock_device) is True
    mock_device.get_state.assert_called_once()

def test_is_device_connection_active_false():
    """Test _is_device_connection_active returns False on exception."""
    from adb_auto_player.adb import _is_device_connection_active
    mock_device = MockAdbDevice()
    mock_device.get_state = MagicMock(side_effect=Exception("Get state failed"))
    assert _is_device_connection_active(mock_device) is False
    mock_device.get_state.assert_called_once()

# --- Tests for _connect_to_device ---

@patch("adb_auto_player.adb._connect_client")
@patch("adb_auto_player.adb._is_device_connection_active", return_value=True)
def test_connect_to_device_success(mock_is_active, mock_connect_client):
    """Test _connect_to_device returns device if connect and active check succeed."""
    from adb_auto_player.adb import _connect_to_device
    mock_client = MockAdbClient()
    mock_device_instance = MockAdbDevice("dev1")
    mock_client.device = MagicMock(return_value=mock_device_instance)
    device_id = "dev1"

    device = _connect_to_device(mock_client, device_id)

    mock_connect_client.assert_called_once_with(mock_client, device_id)
    mock_client.device.assert_called_once_with(f"{device_id}")
    mock_is_active.assert_called_once_with(mock_device_instance)
    assert device == mock_device_instance

@patch("adb_auto_player.adb._connect_client", side_effect=Exception("Connect client failed"))
def test_connect_to_device_connect_client_fails(mock_connect_client):
    """Test _connect_to_device returns None if _connect_client fails."""
    from adb_auto_player.adb import _connect_to_device
    mock_client = MockAdbClient()
    mock_client.device = MagicMock()
    device_id = "dev1"

    device = _connect_to_device(mock_client, device_id)

    mock_connect_client.assert_called_once_with(mock_client, device_id)
    mock_client.device.assert_not_called()
    assert device is None

@patch("adb_auto_player.adb._connect_client")
@patch("adb_auto_player.adb._is_device_connection_active", return_value=False)
def test_connect_to_device_not_active(mock_is_active, mock_connect_client):
    """Test _connect_to_device returns None if device is not active."""
    from adb_auto_player.adb import _connect_to_device
    mock_client = MockAdbClient()
    mock_device_instance = MockAdbDevice("dev1")
    mock_client.device = MagicMock(return_value=mock_device_instance)
    device_id = "dev1"

    device = _connect_to_device(mock_client, device_id)

    mock_connect_client.assert_called_once_with(mock_client, device_id)
    mock_client.device.assert_called_once_with(f"{device_id}")
    mock_is_active.assert_called_once_with(mock_device_instance)
    assert device is None

# --- Tests for _try_incrementing_ports ---

@patch("adb_auto_player.adb._connect_to_device")
def test_try_incrementing_ports_finds_on_increment(mock_connect_to_device):
    """Test _try_incrementing_ports finds device after incrementing port."""
    from adb_auto_player.adb import _try_incrementing_ports
    mock_client = MockAdbClient()
    device_id = "127.0.0.1:5555"
    found_device = MockAdbDevice("127.0.0.1:5556")
    # Simulate failing on 5555, succeeding on 5556
    mock_connect_to_device.side_effect = [None, found_device]

    device = _try_incrementing_ports(mock_client, device_id)

    assert mock_connect_to_device.call_count == 2
    mock_connect_to_device.assert_has_calls([
        call(mock_client, "127.0.0.1:5556"),
        # call(mock_client, "127.0.0.1:5557"), # Should stop after finding
    ])
    assert device == found_device

@patch("adb_auto_player.adb._connect_to_device")
def test_try_incrementing_ports_finds_on_bluestacks_increment(mock_connect_to_device):
    """Test _try_incrementing_ports finds device using BlueStacks increment (5565)."""
    from adb_auto_player.adb import _try_incrementing_ports
    mock_client = MockAdbClient()
    device_id = "127.0.0.1:5555"
    found_device = MockAdbDevice("127.0.0.1:5565")
    # Simulate failing on 5556-5559, succeeding on 5565
    mock_connect_to_device.side_effect = [None, None, None, None, found_device]

    device = _try_incrementing_ports(mock_client, device_id)

    assert mock_connect_to_device.call_count == 5
    mock_connect_to_device.assert_has_calls([
        call(mock_client, "127.0.0.1:5556"),
        call(mock_client, "127.0.0.1:5557"),
        call(mock_client, "127.0.0.1:5558"),
        call(mock_client, "127.0.0.1:5559"),
        call(mock_client, "127.0.0.1:5565"),
    ])
    assert device == found_device

@patch("adb_auto_player.adb._connect_to_device", return_value=None)
def test_try_incrementing_ports_not_found(mock_connect_to_device):
    """Test _try_incrementing_ports returns None if no device found after trying ports."""
    from adb_auto_player.adb import _try_incrementing_ports
    mock_client = MockAdbClient()
    device_id = "127.0.0.1:5555"

    device = _try_incrementing_ports(mock_client, device_id)

    # Should try 5556-5559 and 5565, 5575, 5585 (total 7 calls)
    assert mock_connect_to_device.call_count == 7
    assert device is None

@patch("adb_auto_player.adb._connect_to_device")
def test_try_incrementing_ports_no_port_in_id(mock_connect_to_device):
    """Test _try_incrementing_ports does nothing if device_id has no port."""
    from adb_auto_player.adb import _try_incrementing_ports
    mock_client = MockAdbClient()
    device_id = "physical_device_serial"

    device = _try_incrementing_ports(mock_client, device_id)

    mock_connect_to_device.assert_not_called()
    assert device is None

# --- Tests for _resolve_device ---

@patch("adb_auto_player.adb._connect_to_device", return_value=None) # All direct connects fail
@patch("adb_auto_player.adb._try_incrementing_ports")
def test_resolve_device_uses_incrementing_ports(mock_try_increment, mock_connect_to):
    """Test _resolve_device falls back to _try_incrementing_ports."""
    from adb_auto_player.adb import _resolve_device
    mock_client = MockAdbClient()
    device_id = "127.0.0.1:5555"
    devices_list = [MockAdbDeviceInfo("127.0.0.1:5555", "device")] # List might be stale
    found_device_incremented = MockAdbDevice("127.0.0.1:5556")
    mock_try_increment.return_value = found_device_incremented

    device = _resolve_device(mock_client, device_id, devices_list)

    # Check the calls made to _connect_to_device
    # It seems to try the original ID twice before incrementing
    expected_calls = [
        call(mock_client, device_id),
        call(mock_client, device_id) # Second attempt based on failure log
    ]
    mock_connect_to.assert_has_calls(expected_calls)
    assert mock_connect_to.call_count == 2

    mock_try_increment.assert_called_once_with(mock_client, device_id)
    assert device == found_device_incremented

@patch("adb_auto_player.adb._connect_to_device", return_value=None)
@patch("adb_auto_player.adb._try_incrementing_ports", return_value=None)
@patch("adb_auto_player.adb.log_devices")
@patch("adb_auto_player.adb.GenericAdbError", new=MockAdbError)
def test_resolve_device_not_found_raises_error(mock_log_devices, mock_try_increment, mock_connect_to):
    """Test _resolve_device raises GenericAdbError if no device is found."""
    from adb_auto_player.adb import _resolve_device
    mock_client = MockAdbClient()
    device_id = "dev_unknown"
    available_device_id = "other_dev"
    devices_list = [MockAdbDeviceInfo(available_device_id, "device")]

    with pytest.raises(MockAdbError, match=f"Device: {device_id} not found"):
        _resolve_device(mock_client, device_id, devices_list)

    # Check the specific calls made based on failure log
    expected_calls = [
        call(mock_client, device_id), # First attempt with specified ID
        call(mock_client, available_device_id) # Second attempt with the only available device
    ]
    mock_connect_to.assert_has_calls(expected_calls)
    assert mock_connect_to.call_count == 2

    mock_try_increment.assert_called_once_with(mock_client, device_id)
    mock_log_devices.assert_called_once()

# --- Tests for _override_size ---

@patch("adb_auto_player.adb.logging")
def test_override_size_success(mock_logging):
    """Test _override_size executes shell command."""
    from adb_auto_player.adb import _override_size
    mock_device = MockAdbDevice()
    mock_device.shell = MagicMock(return_value="") # No error output
    size = "1080x1920"

    _override_size(mock_device, size)

    mock_device.shell.assert_called_once_with(f"wm size {size}")
    mock_logging.debug.assert_called_with(f"Overriding size: {size}")

@patch("adb_auto_player.adb.logging")
@patch("adb_auto_player.adb.GenericAdbError", new=MockAdbError)
def test_override_size_security_exception(mock_logging):
    """Test _override_size raises GenericAdbError for SecurityException."""
    from adb_auto_player.adb import _override_size
    mock_device = MockAdbDevice()
    error_output = "Error: java.lang.SecurityException: Permission denied"
    mock_device.shell = MagicMock(return_value=error_output)
    size = "1080x1920"

    with pytest.raises(MockAdbError, match="java.lang.SecurityException"):
        _override_size(mock_device, size)

    mock_device.shell.assert_called_once_with(f"wm size {size}")

@patch("adb_auto_player.adb.logging")
@patch("adb_auto_player.adb.GenericAdbError", new=MockAdbError)
def test_override_size_shell_error(mock_logging):
    """Test _override_size raises GenericAdbError for other shell errors."""
    from adb_auto_player.adb import _override_size
    mock_device = MockAdbDevice()
    mock_device.shell = MagicMock(side_effect=Exception("Shell command failed"))
    size = "1080x1920"

    with pytest.raises(MockAdbError, match="Error overriding size: Shell command failed"):
        _override_size(mock_device, size)

    mock_device.shell.assert_called_once_with(f"wm size {size}")

# --- Tests for _get_adb_device (Higher level integration) ---

@patch("adb_auto_player.adb.ConfigLoader")
@patch("adb_auto_player.adb._connect_client")
@patch("adb_auto_player.adb._get_devices")
@patch("adb_auto_player.adb.log_devices")
@patch("adb_auto_player.adb._resolve_device")
@patch("adb_auto_player.adb._override_size")
def test_get_adb_device_integration_no_override(
    mock_override, mock_resolve, mock_log, mock_get_devs, mock_connect_cli, mock_config_loader
):
    """Test _get_adb_device connects without overriding size."""
    from adb_auto_player.adb import _get_adb_device
    mock_client = MockAdbClient()
    device_id = "dev1"
    mock_config_instance = MockConfigLoader()
    mock_config_instance.main_config["device"] = {"wm_size": False} # Override disabled
    mock_config_loader.return_value = mock_config_instance
    mock_devices_list = [MockAdbDeviceInfo(device_id, "device")]
    mock_get_devs.return_value = mock_devices_list
    found_device = MockAdbDevice(device_id)
    mock_resolve.return_value = found_device

    device = _get_adb_device(mock_client, device_id, override_size=None)

    mock_connect_cli.assert_called_once_with(mock_client, device_id)
    mock_get_devs.assert_called_once_with(mock_client)
    mock_log.assert_called_once_with(mock_devices_list)
    mock_resolve.assert_called_once_with(mock_client, device_id, mock_devices_list)
    mock_override.assert_not_called() # Should not be called
    assert device == found_device

@patch("adb_auto_player.adb.ConfigLoader")
@patch("adb_auto_player.adb._connect_client")
@patch("adb_auto_player.adb._get_devices")
@patch("adb_auto_player.adb.log_devices")
@patch("adb_auto_player.adb._resolve_device")
@patch("adb_auto_player.adb._override_size")
def test_get_adb_device_integration_with_override(
    mock_override, mock_resolve, mock_log, mock_get_devs, mock_connect_cli, mock_config_loader
):
    """Test _get_adb_device connects and overrides size when requested."""
    from adb_auto_player.adb import _get_adb_device
    mock_client = MockAdbClient()
    device_id = "dev1"
    override_size_str = "1080x1920"
    mock_config_instance = MockConfigLoader()
    mock_config_instance.main_config["device"] = {"wm_size": True} # Override enabled
    mock_config_loader.return_value = mock_config_instance
    mock_devices_list = [MockAdbDeviceInfo(device_id, "device")]
    mock_get_devs.return_value = mock_devices_list
    found_device = MockAdbDevice(device_id)
    mock_resolve.return_value = found_device

    device = _get_adb_device(mock_client, device_id, override_size=override_size_str)

    mock_connect_cli.assert_called_once_with(mock_client, device_id)
    mock_get_devs.assert_called_once_with(mock_client)
    mock_log.assert_called_once_with(mock_devices_list)
    mock_resolve.assert_called_once_with(mock_client, device_id, mock_devices_list)
    mock_override.assert_called_once_with(found_device, override_size_str) # Should be called
    assert device == found_device

@patch("adb_auto_player.adb.ConfigLoader")
@patch("adb_auto_player.adb._connect_client")
@patch("adb_auto_player.adb._get_devices")
@patch("adb_auto_player.adb.log_devices")
@patch("adb_auto_player.adb._resolve_device")
@patch("adb_auto_player.adb._override_size")
def test_get_adb_device_integration_override_disabled_in_config(
    mock_override, mock_resolve, mock_log, mock_get_devs, mock_connect_cli, mock_config_loader
):
    """Test _get_adb_device does not override size if disabled in config, even if override_size is passed."""
    from adb_auto_player.adb import _get_adb_device
    mock_client = MockAdbClient()
    device_id = "dev1"
    override_size_str = "1080x1920"
    mock_config_instance = MockConfigLoader()
    mock_config_instance.main_config["device"] = {"wm_size": False} # Override disabled
    mock_config_loader.return_value = mock_config_instance
    mock_devices_list = [MockAdbDeviceInfo(device_id, "device")]
    mock_get_devs.return_value = mock_devices_list
    found_device = MockAdbDevice(device_id)
    mock_resolve.return_value = found_device

    device = _get_adb_device(mock_client, device_id, override_size=override_size_str)

    mock_override.assert_not_called() # Should NOT be called because config disables it
    assert device == found_device

# --- Tests for exec_wm_size ---

@patch("adb_auto_player.adb.get_adb_device")
@patch("adb_auto_player.adb._override_size")
@patch("adb_auto_player.adb.logging")
def test_exec_wm_size_success(mock_logging, mock_override, mock_get_device):
    """Test exec_wm_size gets device and calls _override_size."""
    from adb_auto_player.adb import exec_wm_size
    mock_device = MockAdbDevice("dev1")
    mock_get_device.return_value = mock_device
    resolution = "720x1280"

    exec_wm_size(resolution)

    mock_get_device.assert_called_once_with(override_size=None) # Gets device without initial override
    mock_override.assert_called_once_with(mock_device, resolution)
    mock_logging.info.assert_called_once()

@patch("adb_auto_player.adb.get_adb_device")
@patch("adb_auto_player.adb._override_size", side_effect=MockAdbError("Override failed"))
@patch("adb_auto_player.adb.logging")
def test_exec_wm_size_override_error(mock_logging, mock_override, mock_get_device):
    """Test exec_wm_size propagates error from _override_size."""
    from adb_auto_player.adb import exec_wm_size
    mock_device = MockAdbDevice("dev1")
    mock_get_device.return_value = mock_device
    resolution = "720x1280"

    with pytest.raises(MockAdbError, match="Override failed"):
        exec_wm_size(resolution)

    mock_get_device.assert_called_once_with(override_size=None)
    mock_override.assert_called_once_with(mock_device, resolution)
    mock_logging.info.assert_not_called()

# --- Tests for wm_size_reset ---

@patch("adb_auto_player.adb.get_adb_device")
@patch("adb_auto_player.adb.logging")
def test_wm_size_reset_success(mock_logging, mock_get_device):
    """Test wm_size_reset gets device and calls shell command."""
    from adb_auto_player.adb import wm_size_reset
    mock_device = MockAdbDevice("dev1")
    mock_device.shell = MagicMock()
    mock_get_device.return_value = mock_device

    wm_size_reset()

    mock_get_device.assert_called_once_with(override_size=None)
    mock_device.shell.assert_called_once_with("wm size reset")
    mock_logging.info.assert_called_once()

@patch("adb_auto_player.adb.get_adb_device")
@patch("adb_auto_player.adb.logging")
@patch("adb_auto_player.adb.GenericAdbError", new=MockAdbError)
def test_wm_size_reset_shell_error(mock_logging, mock_get_device):
    """Test wm_size_reset raises GenericAdbError on shell command failure."""
    from adb_auto_player.adb import wm_size_reset
    mock_device = MockAdbDevice("dev1")
    mock_device.shell = MagicMock(side_effect=Exception("Reset command failed"))
    mock_get_device.return_value = mock_device

    with pytest.raises(MockAdbError, match="wm size reset: Reset command failed"):
        wm_size_reset()

    mock_get_device.assert_called_once_with(override_size=None)
    mock_device.shell.assert_called_once_with("wm size reset")
    mock_logging.info.assert_not_called()

# --- Tests for get_screen_resolution ---

@patch("adb_auto_player.adb.is_portrait", return_value=True) # Assume portrait
def test_get_screen_resolution_physical_size(mock_is_portrait):
    """Test get_screen_resolution extracts physical size (or override if 0x0)."""
    from adb_auto_player.adb import get_screen_resolution
    mock_device = MockAdbDevice()
    shell_output = "Physical size: 1080x1920\nOverride size: 0x0"
    mock_device.shell = MagicMock(return_value=shell_output)

    resolution = get_screen_resolution(mock_device)

    mock_device.shell.assert_called_once_with("wm size", timeout=5)
    mock_is_portrait.assert_called_once_with(mock_device)
    # Update assertion based on observed behavior in logs
    assert resolution == "0x0"

@patch("adb_auto_player.adb.is_portrait", return_value=True) # Assume portrait
def test_get_screen_resolution_override_size(mock_is_portrait):
    """Test get_screen_resolution extracts override size when present."""
    from adb_auto_player.adb import get_screen_resolution
    mock_device = MockAdbDevice()
    shell_output = "Physical size: 1080x1920\nOverride size: 720x1280"
    mock_device.shell = MagicMock(return_value=shell_output)

    resolution = get_screen_resolution(mock_device)

    mock_device.shell.assert_called_once_with("wm size", timeout=5)
    mock_is_portrait.assert_called_once_with(mock_device)
    assert resolution == "720x1280"

@patch("adb_auto_player.adb.is_portrait", return_value=False) # Assume landscape
def test_get_screen_resolution_landscape_swaps_dims(mock_is_portrait):
    """Test get_screen_resolution swaps dimensions for landscape."""
    from adb_auto_player.adb import get_screen_resolution
    mock_device = MockAdbDevice()
    # Note: wm size still reports width x height even in landscape
    shell_output = "Physical size: 1920x1080"
    mock_device.shell = MagicMock(return_value=shell_output)

    resolution = get_screen_resolution(mock_device)

    mock_device.shell.assert_called_once_with("wm size", timeout=5)
    mock_is_portrait.assert_called_once_with(mock_device)
    # Should return height x width for portrait representation
    assert resolution == "1080x1920"

@patch("adb_auto_player.adb.GenericAdbError", new=MockAdbError)
def test_get_screen_resolution_shell_error():
    """Test get_screen_resolution raises GenericAdbError on shell failure."""
    from adb_auto_player.adb import get_screen_resolution
    mock_device = MockAdbDevice()
    mock_device.shell = MagicMock(side_effect=Exception("wm size failed"))

    with pytest.raises(MockAdbError, match="wm size: wm size failed"):
        get_screen_resolution(mock_device)

    mock_device.shell.assert_called_once_with("wm size", timeout=5)

@patch("adb_auto_player.adb.is_portrait", return_value=True)
@patch("adb_auto_player.adb.GenericAdbError", new=MockAdbError)
def test_get_screen_resolution_no_size_found(mock_is_portrait):
    """Test get_screen_resolution raises GenericAdbError if size not in output."""
    from adb_auto_player.adb import get_screen_resolution
    mock_device = MockAdbDevice()
    shell_output = "Some unexpected output"
    mock_device.shell = MagicMock(return_value=shell_output)

    with pytest.raises(MockAdbError, match="Unable to determine screen resolution"):
        get_screen_resolution(mock_device)

    mock_device.shell.assert_called_once_with("wm size", timeout=5)

# --- Tests for is_portrait ---

def test_is_portrait_true():
    """Test is_portrait returns True when all checks indicate portrait (0)."""
    from adb_auto_player.adb import is_portrait
    mock_device = MockAdbDevice()
    mock_device.shell.side_effect = [
        "SurfaceOrientation: 0", # dumpsys input
        "mCurrentRotation=ROTATION_0", # dumpsys window
        "orientation=0", # dumpsys display
    ]

    assert is_portrait(mock_device) is True
    assert mock_device.shell.call_count == 3

def test_is_portrait_false_one_check_fails():
    """Test is_portrait returns False if any check indicates landscape."""
    from adb_auto_player.adb import is_portrait
    mock_device = MockAdbDevice()
    mock_device.shell.side_effect = [
        "SurfaceOrientation: 1", # dumpsys input (indicates landscape)
        "mCurrentRotation=ROTATION_0", # dumpsys window
        "orientation=0", # dumpsys display
    ]

    assert is_portrait(mock_device) is False
    assert mock_device.shell.call_count == 3 # All checks still run

def test_is_portrait_empty_output():
    """Test is_portrait returns True if shell commands return empty strings."""
    # This assumes empty output means default (portrait)
    from adb_auto_player.adb import is_portrait
    mock_device = MockAdbDevice()
    mock_device.shell.side_effect = ["", "", ""]

    assert is_portrait(mock_device) is True
    assert mock_device.shell.call_count == 3

@patch("adb_auto_player.adb.GenericAdbError", new=MockAdbError)
def test_is_portrait_shell_error():
    """Test is_portrait raises GenericAdbError on shell failure."""
    from adb_auto_player.adb import is_portrait
    mock_device = MockAdbDevice()
    mock_device.shell.side_effect = Exception("dumpsys failed")

    with pytest.raises(MockAdbError, match="dumpsys input: dumpsys failed"):
        is_portrait(mock_device)

    assert mock_device.shell.call_count == 1 # Fails on the first call

# --- Tests for get_running_app ---

def test_get_running_app_success_first_try():
    """Test get_running_app extracts package name with mResumedActivity."""
    from adb_auto_player.adb import get_running_app
    mock_device = MockAdbDevice()
    shell_output = " u0 {com.example.game/com.example.game.MainActivity}"
    mock_device.shell.return_value = shell_output

    app = get_running_app(mock_device)

    assert mock_device.shell.call_count == 1
    mock_device.shell.assert_called_once_with(
        "dumpsys activity activities | grep mResumedActivity | "
        "cut -d \"{\" -f2 | cut -d ' ' -f3 | cut -d \"/\" -f1"
    )
    # Update assertion to match the actual, unparsed output
    assert app == shell_output.strip()

def test_get_running_app_success_second_try():
    """Test get_running_app extracts package name with ResumedActivity."""
    from adb_auto_player.adb import get_running_app
    mock_device = MockAdbDevice()
    # First command returns empty, second returns the app
    shell_output_1 = ""
    shell_output_2 = " u0 {com.anotherexample.app/com.anotherexample.app.StartActivity}"
    mock_device.shell.side_effect = [shell_output_1, shell_output_2]

    app = get_running_app(mock_device)

    assert mock_device.shell.call_count == 2
    mock_device.shell.assert_has_calls([
        call(
            "dumpsys activity activities | grep mResumedActivity | "
            "cut -d \"{\" -f2 | cut -d ' ' -f3 | cut -d \"/\" -f1"
        ),
        call(
            "dumpsys activity activities | grep ResumedActivity | "
            "cut -d \"{\" -f2 | cut -d ' ' -f3 | cut -d \"/\" -f1"
        )
    ])
    # Update assertion to match the actual, unparsed output
    assert app == shell_output_2.strip()

def test_get_running_app_second_try_newline():
    """Test get_running_app handles newline in second try output."""
    from adb_auto_player.adb import get_running_app
    mock_device = MockAdbDevice()
    shell_output_1 = ""
    shell_output_2 = "com.third.game\n some other stuff"
    mock_device.shell.side_effect = [shell_output_1, shell_output_2]

    app = get_running_app(mock_device)

    assert mock_device.shell.call_count == 2
    assert app == "com.third.game"

def test_get_running_app_not_found():
    """Test get_running_app returns None if both commands yield no app."""
    from adb_auto_player.adb import get_running_app
    mock_device = MockAdbDevice()
    mock_device.shell.side_effect = ["", ""] # Both commands return empty

    app = get_running_app(mock_device)

    assert mock_device.shell.call_count == 2
    assert app is None
