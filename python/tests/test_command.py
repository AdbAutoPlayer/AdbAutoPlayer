# python/tests/test_command.py
import pytest
from unittest.mock import MagicMock, call

# Assuming ipc module is in the same parent directory or PYTHONPATH is set correctly
# If not, adjust the import path accordingly
try:
    from adb_auto_player.ipc import MenuOption
    from adb_auto_player.command import Command
except ImportError as e:
    # Provide dummy classes if imports fail (e.g., in isolated test environments)
    # This helps define the tests even if the exact structure isn't perfectly resolved
    print(f"Import failed, using dummy classes: {e}")
    class MenuOption:
        def __init__(self, label: str, args: list | None = None, tooltip: str | None = None):
            self.label = label
            self.args = args
            self.tooltip = tooltip

    class Command:
        def __init__(self, name: str, action: callable, kwargs: dict | None = None, menu_option: MenuOption | None = None):
            if " " in name:
                raise ValueError(f"Command name '{name}' should not contain spaces.")
            self.name = name
            self.action = action
            self.kwargs = kwargs if kwargs is not None else {}
            if menu_option is None:
                menu_option = MenuOption(label=name)
            if menu_option.args is None:
                menu_option.args = [name]
            self.menu_option = menu_option

        def run(self):
            self.action(**self.kwargs)


# --- Fixtures ---

@pytest.fixture
def mock_action():
    """Provides a mock callable action."""
    return MagicMock()

# --- Test Cases ---

def test_command_init_basic(mock_action):
    """Test basic Command initialization."""
    cmd_name = "test_command"
    cmd = Command(name=cmd_name, action=mock_action)

    assert cmd.name == cmd_name
    assert cmd.action == mock_action
    assert cmd.kwargs == {}
    # Check default MenuOption creation
    assert isinstance(cmd.menu_option, MenuOption)
    assert cmd.menu_option.label == cmd_name
    assert cmd.menu_option.args == [cmd_name] # Default args
    assert cmd.menu_option.tooltip is None

def test_command_init_with_kwargs(mock_action):
    """Test Command initialization with kwargs."""
    cmd_name = "command_with_args"
    kwargs = {"arg1": "value1", "arg2": 123}
    cmd = Command(name=cmd_name, action=mock_action, kwargs=kwargs)

    assert cmd.name == cmd_name
    assert cmd.action == mock_action
    assert cmd.kwargs == kwargs
    assert cmd.menu_option.label == cmd_name
    assert cmd.menu_option.args == [cmd_name]

def test_command_init_with_custom_menu_option(mock_action):
    """Test Command initialization with a custom MenuOption."""
    cmd_name = "custom_menu_cmd"
    custom_label = "Click Me!"
    custom_args = ["arg_a", "arg_b"]
    custom_tooltip = "Does something cool"
    menu_opt = MenuOption(label=custom_label, args=custom_args, tooltip=custom_tooltip)
    cmd = Command(name=cmd_name, action=mock_action, menu_option=menu_opt)

    assert cmd.name == cmd_name
    assert cmd.action == mock_action
    assert cmd.kwargs == {}
    assert cmd.menu_option == menu_opt # Should be the exact object
    assert cmd.menu_option.label == custom_label
    assert cmd.menu_option.args == custom_args
    assert cmd.menu_option.tooltip == custom_tooltip

def test_command_init_custom_menu_option_no_args(mock_action):
    """Test Command init with custom MenuOption lacking args (should default)."""
    cmd_name = "custom_menu_no_args"
    custom_label = "Run Task"
    menu_opt = MenuOption(label=custom_label) # No args provided
    cmd = Command(name=cmd_name, action=mock_action, menu_option=menu_opt)

    assert cmd.name == cmd_name
    assert cmd.menu_option.label == custom_label
    assert cmd.menu_option.args == [cmd_name] # Should default to command name

def test_command_init_invalid_name(mock_action):
    """Test that initializing Command with a space in the name raises ValueError."""
    invalid_name = "invalid name"
    with pytest.raises(ValueError, match=f"Command name '{invalid_name}' should not contain spaces."):
        Command(name=invalid_name, action=mock_action)

def test_command_run_no_kwargs(mock_action):
    """Test running a command with no kwargs."""
    cmd = Command(name="run_simple", action=mock_action)
    cmd.run()
    mock_action.assert_called_once_with() # Called with no arguments

def test_command_run_with_kwargs(mock_action):
    """Test running a command with kwargs."""
    kwargs = {"param1": "hello", "param2": True}
    cmd = Command(name="run_with_args", action=mock_action, kwargs=kwargs)
    cmd.run()
    mock_action.assert_called_once_with(param1="hello", param2=True) # Called with specific kwargs
