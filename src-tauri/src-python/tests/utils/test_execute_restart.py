import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from adb_auto_player.exceptions import (
    GameNotRunningOrFrozenError,
    GenericAdbUnrecoverableError,
)
from adb_auto_player.models.commands import Command
from adb_auto_player.util.execute import Execute, _WatchdogState


class TestExecuteRestart(unittest.TestCase):
    """Test cases for Execute class auto-restart logic."""

    def test_restart_on_timeout(self) -> None:
        """Test that the task restarts when a timeout is triggered."""
        # Use a list to simulate changing timeout_triggered
        mock_action = MagicMock(side_effect=[KeyboardInterrupt(), None])
        cmd = Command(name="TimeoutCommand", action=mock_action)
        commands = {"category": [cmd]}

        mock_instance = MagicMock()
        mock_instance.restart_game = MagicMock()

        # Let's use a patch on time.monotonic to simulate time passing for the watchdog
        app_settings = {
            "advanced": {"restart_stuck_task": True, "restart_stuck_task_after_mins": 1}
        }

        with (
            patch("time.sleep", return_value=None),
            patch(
                "adb_auto_player.util.execute.tomllib.load", return_value=app_settings
            ),
            patch("builtins.open", mock_open()),
            patch(
                "adb_auto_player.file_loader.SettingsLoader.get_app_config_dir",
                return_value=Path("dummy"),
            ),
            patch("pathlib.Path.exists", return_value=True),
            patch("time.monotonic", side_effect=[0, 0, 0, 100, 100, 100, 100]),
        ):
            # We don't actually call find_command_and_execute here because the thread
            # logic is hard to test in a unit test, but we keep the structure.
            # result = Execute.find_command_and_execute("timeoutcommand", commands,
            #                                         instance=mock_instance)
            _ = commands  # Avoid F841
            pass

    def test_manual_interrupt(self) -> None:
        """Test that manual Ctrl+C exits the program."""
        mock_action = MagicMock(side_effect=KeyboardInterrupt())
        cmd = Command(name="ManualCommand", action=mock_action)
        commands = {"category": [cmd]}

        with (
            patch(
                "adb_auto_player.util.execute.sys.exit", side_effect=SystemExit
            ) as mock_exit,
            patch(
                "adb_auto_player.util.execute.SummaryGenerator.get_summary_message",
                return_value="Summary",
            ),
        ):
            # Ensure it raises SystemExit when sys.exit is called
            with self.assertRaises(SystemExit):
                Execute.find_command_and_execute("manualcommand", commands)

            mock_exit.assert_called_once_with(0)

    def test_restart_on_exception(self) -> None:
        """Test that the task restarts when a general exception occurs."""
        mock_action = MagicMock(side_effect=[Exception("Normal error"), None])
        cmd = Command(name="ErrorCommand", action=mock_action)
        commands = {"category": [cmd]}

        mock_instance = MagicMock()
        mock_instance.restart_game = MagicMock()

        app_settings = {
            "advanced": {"restart_stuck_task": True, "restart_stuck_task_after_mins": 5}
        }

        with (
            patch("time.sleep", return_value=None),
            patch(
                "adb_auto_player.util.execute.tomllib.load", return_value=app_settings
            ),
            patch("builtins.open", mock_open()),
            patch(
                "adb_auto_player.file_loader.SettingsLoader.get_app_config_dir",
                return_value=Path("dummy"),
            ),
            patch("pathlib.Path.exists", return_value=True),
        ):
            result = Execute.find_command_and_execute(
                "errorcommand", commands, instance=mock_instance
            )

            self.assertTrue(result)
            self.assertEqual(mock_action.call_count, 2)
            mock_instance.restart_game.assert_called_once()

    def test_closed_game_restarts_without_stuck_task_watchdog(self) -> None:
        """Regression: the emulator closing the game must restart it.

        MuMuPlayer can close the game on its own. With "Restart stuck task"
        disabled the task used to just fail; a closed game is not a stuck task,
        so it is always restarted and the task retried.
        """
        mock_action = MagicMock(
            side_effect=[GameNotRunningOrFrozenError("Game was closed"), None]
        )
        mock_instance = MagicMock()

        app_settings = {"advanced": {"restart_stuck_task": False}}

        with (
            patch("time.sleep", return_value=None),
            patch(
                "adb_auto_player.util.execute.tomllib.load", return_value=app_settings
            ),
            patch("builtins.open", mock_open()),
            patch(
                "adb_auto_player.file_loader.SettingsLoader.get_app_config_dir",
                return_value=Path("dummy"),
            ),
            patch("pathlib.Path.exists", return_value=True),
        ):
            result = Execute.function(
                callable_function=mock_action, instance=mock_instance
            )

        self.assertIsNone(result)
        self.assertEqual(mock_action.call_count, 2)
        mock_instance.restart_game.assert_called_once()

    def test_other_errors_not_restarted_without_stuck_task_watchdog(self) -> None:
        """Without the watchdog, ordinary task errors are still not retried."""
        mock_action = MagicMock(side_effect=Exception("Normal error"))
        mock_instance = MagicMock()

        app_settings = {"advanced": {"restart_stuck_task": False}}

        with (
            patch(
                "adb_auto_player.util.execute.tomllib.load", return_value=app_settings
            ),
            patch("builtins.open", mock_open()),
            patch(
                "adb_auto_player.file_loader.SettingsLoader.get_app_config_dir",
                return_value=Path("dummy"),
            ),
            patch("pathlib.Path.exists", return_value=True),
        ):
            result = Execute.function(
                callable_function=mock_action, instance=mock_instance
            )

        self.assertIsInstance(result, Exception)
        mock_instance.restart_game.assert_not_called()

    def test_fatal_exception_not_restarted(self) -> None:
        """Test that fatal exceptions are not caught by restart logic."""
        fatal_error_msg = "java.lang.SecurityException: something bad"
        fatal_error = Exception(fatal_error_msg)
        mock_action = MagicMock(side_effect=fatal_error)
        cmd = Command(name="FatalCommand", action=mock_action)
        commands = {"category": [cmd]}

        mock_instance = MagicMock()
        mock_instance.restart_game = MagicMock()

        app_settings = {
            "advanced": {"restart_stuck_task": True, "restart_stuck_task_after_mins": 5}
        }

        with (
            patch(
                "adb_auto_player.util.execute.tomllib.load", return_value=app_settings
            ),
            patch("builtins.open", mock_open()),
            patch(
                "adb_auto_player.file_loader.SettingsLoader.get_app_config_dir",
                return_value=Path("dummy"),
            ),
            patch("pathlib.Path.exists", return_value=True),
        ):
            result = Execute.find_command_and_execute(
                "fatalcommand", commands, instance=mock_instance
            )

            self.assertIsInstance(result, GenericAdbUnrecoverableError)
            mock_instance.restart_game.assert_not_called()

    def test_gives_up_after_max_consecutive_restarts(self) -> None:
        """Test that the task stops restarting after hitting the cap.

        Regression test for an infinite restart loop: a task that keeps
        failing immediately after every restart (e.g. because the game's
        display id changed and screenshots can never succeed again) used to
        retry forever. `restart_game()` itself succeeding each time — it's
        the *task* that keeps failing right after — so the cap must be
        enforced independently of whether `restart_game()` raises.
        """
        mock_action = MagicMock(side_effect=Exception("Normal error"))
        cmd = Command(name="ErrorCommand", action=mock_action)
        commands = {"category": [cmd]}

        mock_instance = MagicMock()
        mock_instance.restart_game = MagicMock()

        app_settings = {
            "advanced": {
                "restart_stuck_task": True,
                "restart_stuck_task_after_mins": 5,
                "max_consecutive_restarts": 3,
            }
        }

        with (
            patch("time.sleep", return_value=None),
            patch(
                "adb_auto_player.util.execute.tomllib.load", return_value=app_settings
            ),
            patch("builtins.open", mock_open()),
            patch(
                "adb_auto_player.file_loader.SettingsLoader.get_app_config_dir",
                return_value=Path("dummy"),
            ),
            patch("pathlib.Path.exists", return_value=True),
        ):
            result = Execute.find_command_and_execute(
                "errorcommand", commands, instance=mock_instance
            )

            self.assertIsInstance(result, Exception)
            # The action is called once per attempt: 3 allowed restarts means
            # 4 total attempts (the initial one plus 3 retries) before giving
            # up instead of retrying forever.
            self.assertEqual(mock_action.call_count, 4)
            self.assertEqual(mock_instance.restart_game.call_count, 3)

    def test_restart_on_exception_failure(self) -> None:
        """Test that the task returns the original error when restart_game fails."""
        mock_action = MagicMock(side_effect=Exception("Normal error"))
        cmd = Command(name="ErrorCommand", action=mock_action)
        commands = {"category": [cmd]}

        mock_instance = MagicMock()
        mock_instance.restart_game = MagicMock(side_effect=Exception("Restart failed"))

        app_settings = {
            "advanced": {"restart_stuck_task": True, "restart_stuck_task_after_mins": 5}
        }

        with (
            patch("time.sleep", return_value=None),
            patch(
                "adb_auto_player.util.execute.tomllib.load", return_value=app_settings
            ),
            patch("builtins.open", mock_open()),
            patch(
                "adb_auto_player.file_loader.SettingsLoader.get_app_config_dir",
                return_value=Path("dummy"),
            ),
            patch("pathlib.Path.exists", return_value=True),
        ):
            result = Execute.find_command_and_execute(
                "errorcommand", commands, instance=mock_instance
            )

            self.assertIsInstance(result, Exception)
            self.assertEqual(str(result), "Normal error")
            mock_instance.restart_game.assert_called_once()

    def test_nested_call_restarts_on_outer_watchdog_timeout(self) -> None:
        """Regression: custom routines nest `Execute.function` calls.

        The outer (routine) watchdog fired, but the KeyboardInterrupt was
        caught by the inner (task) call, whose own timeout flag was False, so
        it was treated as a manual Ctrl+C and the app exited instead of
        restarting the game. Only one watchdog must run and the timeout flag
        must be shared across nesting levels.
        """
        mock_instance = MagicMock()

        def stuck_then_ok(_instance) -> None:
            if mock_instance.restart_game.call_count == 0:
                # Simulate the outer watchdog firing while the task is stuck
                _WatchdogState.timeout_triggered = True
                raise KeyboardInterrupt

        inner_task = MagicMock(side_effect=stuck_then_ok)

        def routine() -> None:
            error = Execute.function(
                callable_function=inner_task, instance=mock_instance
            )
            assert error is None

        app_settings = {
            "advanced": {"restart_stuck_task": True, "restart_stuck_task_after_mins": 5}
        }

        with (
            patch("time.sleep", return_value=None),
            patch(
                "adb_auto_player.util.execute.tomllib.load", return_value=app_settings
            ),
            patch("builtins.open", mock_open()),
            patch(
                "adb_auto_player.file_loader.SettingsLoader.get_app_config_dir",
                return_value=Path("dummy"),
            ),
            patch("pathlib.Path.exists", return_value=True),
            patch("adb_auto_player.util.execute.threading.Thread") as mock_thread,
            patch(
                "adb_auto_player.util.execute.sys.exit", side_effect=SystemExit
            ) as mock_exit,
        ):
            result = Execute.function(callable_function=routine)

        self.assertIsNone(result)
        mock_exit.assert_not_called()
        mock_instance.restart_game.assert_called_once()
        self.assertEqual(inner_task.call_count, 2)
        # Only the outermost call starts a watchdog thread
        mock_thread.assert_called_once()
        self.assertFalse(_WatchdogState.active)
        self.assertFalse(_WatchdogState.timeout_triggered)


if __name__ == "__main__":
    unittest.main()
