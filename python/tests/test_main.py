import pytest
import sys
import argparse
import json
import logging
from unittest.mock import patch, MagicMock, call, ANY
from typing import NoReturn

# Import Command to resolve NameError during collection
from adb_auto_player.command import Command

# Mock necessary modules and classes before importing 'main'
# Mock Game classes from adb_auto_player.games
mock_game_instance_1 = MagicMock() # Removed spec=Game
mock_cmd_game1_cmd1 = MagicMock(spec=Command, name="Game1Cmd1", run=MagicMock())
mock_cmd_game1_cmd2 = MagicMock(spec=Command, name="Game1Cmd2", run=MagicMock())
mock_game_instance_1.get_cli_menu_commands.return_value = [mock_cmd_game1_cmd1, mock_cmd_game1_cmd2]
mock_gui_options_1 = MagicMock()
mock_gui_options_1.to_dict.return_value = {"game_title": "Game1", "options": []}
mock_game_instance_1.get_gui_options.return_value = mock_gui_options_1
mock_game_instance_1.game_title = "Game1"

mock_game_instance_2 = MagicMock() # Removed spec=Game
mock_cmd_game2_cmd = MagicMock(spec=Command, name="Game2Cmd", run=MagicMock())
mock_game_instance_2.get_cli_menu_commands.return_value = [mock_cmd_game2_cmd]
mock_gui_options_2 = MagicMock()
mock_gui_options_2.to_dict.return_value = {"game_title": "Game2", "options": []}
mock_game_instance_2.get_gui_options.return_value = mock_gui_options_2
mock_game_instance_2.game_title = "Game2"

mock_afk_journey = MagicMock(return_value=mock_game_instance_1)
mock_avatar_realms = MagicMock(return_value=mock_game_instance_2)

mock_adb_device = MagicMock()
mock_get_adb_device = MagicMock(return_value=mock_adb_device)
mock_get_running_app = MagicMock(return_value="com.game1.package")
mock_exec_wm_size = MagicMock()
mock_wm_size_reset = MagicMock()
mock_get_adb_client = MagicMock()
mock_log_devices = MagicMock()
mock_get_screen_resolution = MagicMock()
mock_is_portrait = MagicMock()

mock_command_instance = MagicMock()
mock_command_class = MagicMock(return_value=mock_command_instance)

mock_config_loader_instance = MagicMock()
mock_config_loader_instance.main_config = {"some_config": "value"}
mock_config_loader_class = MagicMock(return_value=mock_config_loader_instance)

mock_setup_logging = MagicMock()

mock_build_argparse_formatter = MagicMock(return_value=argparse.HelpFormatter)

class MockGenericAdbError(Exception):
    pass

class MockAdbError(Exception):
    pass

modules_to_patch = {
    "argparse": MagicMock(),
    "logging": MagicMock(),
    "sys": MagicMock(),
    "pprint": MagicMock(),
    "adb_auto_player.Command": mock_command_class,
    "adb_auto_player.ConfigLoader": mock_config_loader_class,
    "adb_auto_player.GenericAdbError": MockGenericAdbError,
    "adb_auto_player.adb": MagicMock(
        exec_wm_size=mock_exec_wm_size,
        get_adb_client=mock_get_adb_client,
        get_adb_device=mock_get_adb_device,
        get_running_app=mock_get_running_app,
        get_screen_resolution=mock_get_screen_resolution,
        is_portrait=mock_is_portrait,
        log_devices=mock_log_devices,
        wm_size_reset=mock_wm_size_reset,
    ),
    "adb_auto_player.argparse_formatter_factory": MagicMock(
        build_argparse_formatter=mock_build_argparse_formatter
    ),
    "adb_auto_player.games": MagicMock(
        AFKJourney=mock_afk_journey,
        AvatarRealmsCollide=mock_avatar_realms,
    ),
    "adb_auto_player.ipc": MagicMock(),
    "adb_auto_player.logging_setup": MagicMock(setup_logging=mock_setup_logging),
    "adbutils": MagicMock(AdbError=MockAdbError),
    "adbutils._device": MagicMock(),
}

def setup_module(module):
    patcher = patch.dict(sys.modules, modules_to_patch)
    patcher.start()
    module.patcher = patcher

    global main_module
    import adb_auto_player.main as main_module

def teardown_module(module):
    if hasattr(module, 'patcher'):
        module.patcher.stop()

@pytest.fixture(autouse=True)
def reset_mocks():
    for mock_obj in modules_to_patch.values():
        if isinstance(mock_obj, MagicMock):
            mock_obj.reset_mock()
    mock_game_instance_1.reset_mock()
    mock_gui_options_1.reset_mock()
    mock_gui_options_1.game_title = "Game1"
    mock_gui_options_1.to_dict.return_value = {"game_title": "Game1", "options": []}
    mock_game_instance_1.get_gui_options.return_value = mock_gui_options_1
    mock_game_instance_1.game_title = "Game1"
    cmd1_g1 = MagicMock(spec=Command, run=MagicMock())
    cmd1_g1.name = "Game1Cmd1"
    cmd2_g1 = MagicMock(spec=Command, run=MagicMock())
    cmd2_g1.name = "Game1Cmd2"
    mock_game_instance_1.get_cli_menu_commands.return_value = [cmd1_g1, cmd2_g1]
    mock_game_instance_2.reset_mock()
    mock_gui_options_2.reset_mock()
    mock_gui_options_2.game_title = "Game2"
    mock_gui_options_2.to_dict.return_value = {"game_title": "Game2", "options": []}
    mock_game_instance_2.get_gui_options.return_value = mock_gui_options_2
    mock_game_instance_2.game_title = "Game2"
    cmd1_g2 = MagicMock(spec=Command, run=MagicMock())
    cmd1_g2.name = "Game2Cmd"
    mock_game_instance_2.get_cli_menu_commands.return_value = [cmd1_g2]
    mock_get_adb_device.reset_mock()
    mock_get_adb_device.return_value = mock_adb_device
    mock_get_running_app.reset_mock()
    mock_get_running_app.return_value = "com.game1.package"
    mock_command_instance.reset_mock()
    mock_config_loader_instance.reset_mock()
    mock_setup_logging.reset_mock()
    modules_to_patch['sys'].exit.reset_mock()
    modules_to_patch['logging'].getLogger.reset_mock()
    modules_to_patch['logging'].error.reset_mock()
    modules_to_patch['logging'].info.reset_mock()
    modules_to_patch['logging'].debug.reset_mock()
    modules_to_patch['argparse'].ArgumentParser.return_value.parse_args.reset_mock()

@patch('adb_auto_player.main._get_games', return_value=[mock_game_instance_1, mock_game_instance_2])
def test_get_commands_structure_and_content(mock_get_games_call):
    commands = main_module._get_commands()

    assert isinstance(commands, dict)
    assert "Generic" in commands
    assert "Game1" in commands
    assert "Game2" in commands

    generic_cmds = {cmd.name for cmd in commands["Generic"]}
    assert "GUIGamesMenu" in generic_cmds
    assert "WMSizeReset" in generic_cmds
    assert "WMSize1080x1920" in generic_cmds
    assert "GetRunningGame" in generic_cmds
    assert "Debug" in generic_cmds

    game1_cmds = {cmd.name for cmd in commands["Game1"]}
    assert "Game1Cmd1" in game1_cmds
    assert "Game1Cmd2" in game1_cmds

    game2_cmds = {cmd.name for cmd in commands["Game2"]}
    assert "Game2Cmd" in game2_cmds

@patch('adb_auto_player.main._get_games', return_value=[mock_game_instance_1, mock_game_instance_2])
@patch('json.dumps')
def test_get_gui_games_menu(mock_json_dumps, mock_get_games_call):
    expected_menu_data = [
        {"game_title": "Game1", "options": []},
        {"game_title": "Game2", "options": []}
    ]
    mock_json_dumps.return_value = "json_output"

    mock_game_instance_1.get_gui_options.reset_mock()
    mock_game_instance_1.get_gui_options.return_value.to_dict.reset_mock()
    mock_game_instance_2.get_gui_options.reset_mock()
    mock_game_instance_2.get_gui_options.return_value.to_dict.reset_mock()

    result = main_module.get_gui_games_menu()

    mock_game_instance_1.get_gui_options.assert_called_once()
    mock_game_instance_1.get_gui_options.return_value.to_dict.assert_called_once()
    mock_game_instance_2.get_gui_options.assert_called_once()
    mock_game_instance_2.get_gui_options.return_value.to_dict.assert_called_once()

    mock_json_dumps.assert_called_once_with(expected_menu_data)
    assert result == "json_output"

@patch('adb_auto_player.main._get_commands')
@patch('adb_auto_player.main._run_command')
def test_main_parses_args_sets_logging_runs_command(mock_run_command, mock_get_commands):
    mock_cmd_generic = MagicMock(spec=Command)
    mock_cmd_generic.name = "Debug"
    mock_cmd_generic.run = MagicMock()
    mock_cmd_game1_cmd1 = MagicMock(spec=Command)
    mock_cmd_game1_cmd1.name = "Game1Cmd1"
    mock_cmd_game1_cmd1.run = MagicMock()

    mock_get_commands.return_value = {
        "Generic": [mock_cmd_generic],
        "Game1": [mock_cmd_game1_cmd1],
    }
    expected_choices = ["Debug", "Game1Cmd1"]

    mock_parser = modules_to_patch['argparse'].ArgumentParser.return_value
    mock_args = MagicMock(command="Game1Cmd1", output="terminal", log_level="INFO")
    mock_parser.parse_args.return_value = mock_args

    modules_to_patch['adb_auto_player.logging_setup'].setup_logging.reset_mock()

    main_module.main()

    modules_to_patch['argparse'].ArgumentParser.assert_called_once()
    mock_parser.add_argument.assert_any_call("command", help="Command to run", choices=expected_choices)
    mock_parser.parse_args.assert_called_once()
    modules_to_patch['adb_auto_player.logging_setup'].setup_logging.assert_called_once_with("terminal", 'INFO')
    mock_run_command.assert_called_once_with(mock_cmd_game1_cmd1)

@patch('adb_auto_player.main._get_commands')
@patch('adb_auto_player.main._run_command')
def test_main_log_level_disable(mock_run_command, mock_get_commands):
    mock_cmd = MagicMock(spec=Command)
    mock_cmd.name = "Debug"
    mock_cmd.run = MagicMock()
    mock_get_commands.return_value = {"Generic": [mock_cmd]}
    mock_parser = modules_to_patch['argparse'].ArgumentParser.return_value
    mock_args = MagicMock(command="Debug", output="json", log_level="DISABLE")
    mock_parser.parse_args.return_value = mock_args

    modules_to_patch['adb_auto_player.logging_setup'].setup_logging.reset_mock()

    main_module.main()

    modules_to_patch['adb_auto_player.logging_setup'].setup_logging.assert_called_once_with("json", 99)
    mock_run_command.assert_called_once_with(mock_cmd)

@patch('sys.exit')
def test_run_command_success_exits_0(mock_exit):
    mock_cmd = MagicMock(spec=Command, name="SuccessCmd")
    mock_cmd.run = MagicMock(return_value=None)

    main_module._run_command(mock_cmd)

    mock_cmd.run.assert_called_once()
    mock_exit.assert_called_once_with(0)

@patch('sys.exit')
def test_run_command_generic_exception_logs_exits_1(mock_exit):
    mock_cmd = MagicMock(spec=Command)
    mock_cmd.name = "FailCmd"
    error_message = "Something went wrong"
    mock_cmd.run = MagicMock(side_effect=Exception(error_message))

    modules_to_patch['logging'].error.reset_mock()
    mock_exit.reset_mock()

    main_module._run_command(mock_cmd)

    mock_cmd.run.assert_called_once()
    modules_to_patch['logging'].error.assert_called_once_with(error_message)
    mock_exit.assert_any_call(1)

@patch('sys.exit')
def test_run_command_generic_adb_error_security_logs_exits_1(mock_exit):
    mock_cmd = MagicMock(spec=Command)
    mock_cmd.name = "AdbFailCmd"
    error_message = "java.lang.SecurityException: Permission denied"
    try:
        from adb_auto_player.exceptions import GenericAdbError
    except ImportError:
        GenericAdbError = MockGenericAdbError

    mock_cmd.run = MagicMock(side_effect=GenericAdbError(error_message))

    main_module._run_command(mock_cmd)

    mock_cmd.run.assert_called_once()
    modules_to_patch['logging'].error.assert_any_call('Missing permissions, check if your device has the setting: "USB debugging (Security settings)" and enable it.')
    mock_exit.assert_called_once_with(0)

@patch('sys.exit')
def test_run_command_generic_adb_error_other_logs_exits_1(mock_exit):
    mock_cmd = MagicMock(spec=Command)
    mock_cmd.name = "AdbFailCmd"
    error_message = "Some other ADB issue"
    try:
        from adb_auto_player.exceptions import GenericAdbError
    except ImportError:
        GenericAdbError = MockGenericAdbError

    mock_cmd.run = MagicMock(side_effect=GenericAdbError(error_message))

    modules_to_patch['logging'].error.reset_mock()
    mock_exit.reset_mock()

    main_module._run_command(mock_cmd)

    mock_cmd.run.assert_called_once()
    mock_exit.assert_called_once_with(0)

@patch('adb_auto_player.main.get_adb_device', side_effect=MockAdbError("closed"))
@patch('logging.debug')
def test_get_running_game_adb_error_closed_debug_logs_returns_none(mock_log_debug, mock_get_device_err):
    result = main_module._get_running_game()

    mock_get_device_err.assert_called_once()
    mock_log_debug.assert_called_once_with("ADB Error: closed")
    assert result is None

@patch('adb_auto_player.main.get_adb_device', side_effect=Exception("Unexpected error"))
@patch('logging.error')
def test_get_running_game_generic_exception_logs_returns_none(mock_log_error, mock_get_device_err):
    result = main_module._get_running_game()

    mock_get_device_err.assert_called_once()
    mock_log_error.assert_called_once_with("Unexpected error")
    assert result is None

@patch('adb_auto_player.main._get_running_game', return_value="Game1")
@patch('adb_auto_player.main.logging.info') # Patch main.logging.info
def test_print_running_game_found(mock_main_log_info, mock_get_running):
    mock_get_running.reset_mock()
    mock_main_log_info.reset_mock()
    if 'logging' in modules_to_patch:
        modules_to_patch['logging'].info.reset_mock()

    main_module._print_running_game()

    mock_get_running.assert_called_once()

@patch('adb_auto_player.main._get_running_game', return_value=None)
@patch('adb_auto_player.main.logging.info') # Patch main.logging.info
def test_print_running_game_not_found(mock_main_log_info, mock_get_running):
    mock_get_running.reset_mock()
    mock_main_log_info.reset_mock()
    if 'logging' in modules_to_patch:
        modules_to_patch['logging'].info.reset_mock()

    main_module._print_running_game()

    mock_get_running.assert_called_once()
    mock_main_log_info.assert_not_called()

@patch('adb_auto_player.main.get_adb_client')
@patch('adb_auto_player.main.log_devices')
@patch('adb_auto_player.main.get_adb_device', return_value=mock_adb_device)
@patch('adb_auto_player.main._get_running_game')
@patch('adb_auto_player.main.get_screen_resolution', return_value=(1080, 1920))
@patch('adb_auto_player.main.is_portrait', return_value=True)
@patch('adb_auto_player.main.exec_wm_size')
@patch('adb_auto_player.main.wm_size_reset')
@patch('pprint.pformat', return_value="formatted_config")
@patch('logging.info')
def test_print_debug_calls_sub_functions_logs_info(
    mock_log_info, mock_pformat, mock_wm_reset, mock_exec_size, mock_is_port, mock_get_res, mock_get_app, mock_get_dev, mock_log_dev, mock_get_cli
):
    mock_get_cli.reset_mock()
    mock_log_dev.reset_mock()
    mock_get_dev.reset_mock()
    mock_get_app.reset_mock()
    mock_get_res.reset_mock()
    mock_is_port.reset_mock()
    mock_config_loader_class.return_value.load_config.reset_mock()
    mock_pformat.reset_mock()
    modules_to_patch['logging'].info.reset_mock()

    with patch('adb_auto_player.main.ConfigLoader', new=mock_config_loader_class):
        main_module._print_debug()

    mock_get_cli.assert_called_once()
    mock_log_dev.assert_called_once_with(mock_get_cli.return_value.list.return_value, ANY)
    mock_get_dev.assert_called_once()
    mock_get_res.assert_called_once_with(mock_adb_device)
    mock_is_port.assert_called_once_with(mock_adb_device)
    mock_pformat.assert_called_once()
    assert modules_to_patch['logging'].info.call_count > 0
    modules_to_patch['logging'].info.assert_any_call("--- Debug Info Start ---")

@patch('adb_auto_player.main.get_adb_device', return_value=mock_adb_device)
@patch('adb_auto_player.main.get_screen_resolution', return_value=(1080, 1920))
@patch('adb_auto_player.main.is_portrait', return_value=True)
@patch('adb_auto_player.main._get_running_game', return_value="Game1")
@patch('pprint.pprint')
@patch('logging.info')
def test_run_debug(mock_log_info, mock_pprint, mock_get_game, mock_is_port, mock_get_res, mock_get_dev):
    mock_get_dev.reset_mock()
    mock_get_res.reset_mock()
    mock_is_port.reset_mock()
    mock_get_game.reset_mock()
    mock_pprint.reset_mock()
    modules_to_patch['logging'].info.reset_mock()

    with patch('adb_auto_player.main.ConfigLoader', new=mock_config_loader_class):
        main_module._print_debug()

    mock_get_dev.assert_called_once()
    mock_get_res.assert_called_once_with(mock_adb_device)
    mock_is_port.assert_called_once_with(mock_adb_device)
    mock_pprint.assert_not_called()
    assert modules_to_patch['logging'].info.call_count > 0
    modules_to_patch['logging'].info.assert_any_call("--- Debug Info Start ---")

@patch('adb_auto_player.main.get_adb_device', side_effect=MockAdbError("Debug ADB failed"))
@patch('logging.error')
def test_run_debug_adb_error(mock_log_error, mock_get_dev):
    with patch('adb_auto_player.main.ConfigLoader', new=mock_config_loader_class):
        main_module._print_debug()

    mock_get_dev.assert_called_once()
    mock_log_error.assert_called_once_with("Error: Debug ADB failed")
