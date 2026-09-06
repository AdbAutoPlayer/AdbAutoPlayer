# ruff: noqa: E402
import sys
from unittest.mock import MagicMock

# Mock pytauri and adb_auto_player.ext_mod to bypass import/compilation limitations
# in a standard pytest/python environment.
mock_pytauri = MagicMock()
mock_pytauri.Commands = MagicMock
mock_pytauri.AppHandle = MagicMock
mock_pytauri.Event = MagicMock
mock_pytauri.Listener = MagicMock
mock_pytauri.Manager = MagicMock
mock_pytauri.builder_factory = MagicMock
mock_pytauri.context_factory = MagicMock


class MockEmitter:
    def emit(self, *args, **kwargs):
        pass


mock_pytauri.Emitter = MockEmitter

sys.modules["pytauri"] = mock_pytauri
sys.modules["adb_auto_player.ext_mod"] = MagicMock()

from unittest.mock import patch

import adb_auto_player.__main__ as main_mod
import pytest
from adb_auto_player.__main__ import StartTaskBody, start_task


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_start_task_e2e_flow():
    """E2E flow test for start_task command with process and emitter mocks."""
    app_handle_mock = MagicMock()
    body = StartTaskBody(
        profile_index=0,
        args=["AFKStages", "--season", "False"],
        label="AFK Stages",
    )

    # Setup the config directories in main module
    main_mod._base_app_config_dir = MagicMock()
    main_mod._base_resource_dir = MagicMock()

    # Mock the multiprocessing.Process to control its lifecycle
    mock_process = MagicMock()
    # Simulates running twice, then stopping
    mock_process.is_alive.side_effect = [True, True, False]
    mock_process.exitcode = 0

    # Mock Queue messages
    mock_queue = MagicMock()
    mock_queue.empty.side_effect = [False, True]
    mock_queue.get_nowait.return_value = "Success: 5 stages cleared"

    with (
        patch(
            "adb_auto_player.__main__.Process", return_value=mock_process
        ) as mock_process_cls,
        patch("adb_auto_player.__main__.Queue", return_value=mock_queue),
        patch("adb_auto_player.__main__.QueueListener") as mock_listener_cls,
        patch("adb_auto_player.__main__.Emitter.emit") as mock_emit,
    ):
        # Run start_task
        await start_task(app_handle_mock, body)

        # Assert process was created with correct args
        mock_process_cls.assert_called_once()
        _, kwargs = mock_process_cls.call_args
        assert kwargs["target"].__name__ == "run_task"
        assert kwargs["args"][0] == "AFKStages --season False"

        # Assert listener was started and stopped
        mock_listener_cls.return_value.start.assert_called_once()
        mock_listener_cls.return_value.stop.assert_called_once()

        # Assert that the exit event was emitted
        completed_call = next(
            call for call in mock_emit.call_args_list if call[0][1] == "task-completed"
        )
        payload = completed_call[0][2]
        assert payload.profile_index == 0
        assert payload.msg == "Success: 5 stages cleared"
        assert payload.exit_code == 0


@pytest.mark.anyio
async def test_start_task_retries_on_access_violation_then_succeeds():
    """A STATUS_ACCESS_VIOLATION crash is retried instead of failing.

    Simulates a transient GPU/driver init race - the same task should be
    relaunched automatically rather than surfaced as a final failure.
    """
    app_handle_mock = MagicMock()
    body = StartTaskBody(
        profile_index=0,
        args=["GuildManagerScan"],
        label="Guild Manager Scan",
    )

    main_mod._base_app_config_dir = MagicMock()
    main_mod._base_resource_dir = MagicMock()

    crashed_process = MagicMock()
    crashed_process.is_alive.side_effect = [True, False]
    crashed_process.exitcode = main_mod._STATUS_ACCESS_VIOLATION_EXIT_CODES[0]

    successful_process = MagicMock()
    successful_process.is_alive.side_effect = [True, False]
    successful_process.exitcode = 0

    mock_queue = MagicMock()
    mock_queue.empty.return_value = True

    with (
        patch(
            "adb_auto_player.__main__.Process",
            side_effect=[crashed_process, successful_process],
        ) as mock_process_cls,
        patch("adb_auto_player.__main__.Queue", return_value=mock_queue),
        patch("adb_auto_player.__main__.QueueListener"),
        patch("adb_auto_player.__main__.Emitter.emit") as mock_emit,
    ):
        await start_task(app_handle_mock, body)

        # Retried exactly once: crashed process, then a fresh one that succeeded.
        assert mock_process_cls.call_count == 2

        completed_call = next(
            call for call in mock_emit.call_args_list if call[0][1] == "task-completed"
        )
        payload = completed_call[0][2]
        assert payload.exit_code == 0


@pytest.mark.anyio
async def test_start_task_does_not_retry_normal_failure():
    """A regular (non-crash) failure exit code is surfaced immediately."""
    app_handle_mock = MagicMock()
    body = StartTaskBody(
        profile_index=0,
        args=["AFKStages"],
        label="AFK Stages",
    )

    main_mod._base_app_config_dir = MagicMock()
    main_mod._base_resource_dir = MagicMock()

    failed_process = MagicMock()
    failed_process.is_alive.side_effect = [True, False]
    failed_process.exitcode = 1

    mock_queue = MagicMock()
    mock_queue.empty.return_value = True

    with (
        patch(
            "adb_auto_player.__main__.Process", return_value=failed_process
        ) as mock_process_cls,
        patch("adb_auto_player.__main__.Queue", return_value=mock_queue),
        patch("adb_auto_player.__main__.QueueListener"),
        patch("adb_auto_player.__main__.Emitter.emit") as mock_emit,
    ):
        await start_task(app_handle_mock, body)

        mock_process_cls.assert_called_once()

        completed_call = next(
            call for call in mock_emit.call_args_list if call[0][1] == "task-completed"
        )
        payload = completed_call[0][2]
        assert payload.exit_code == 1
