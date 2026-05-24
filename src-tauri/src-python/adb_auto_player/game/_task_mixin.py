"""Task execution mixin — custom routines and error handling."""

import logging
import sys

import cv2
from adb_auto_player.exceptions import (
    AutoPlayerError,
    AutoPlayerUnrecoverableError,
    GameNotRunningOrFrozenError,
)
from adb_auto_player.image_manipulation import IO
from adb_auto_player.models.pydantic import TaskListSettings
from adb_auto_player.models.registries import CustomRoutineEntry
from adb_auto_player.registries import CUSTOM_ROUTINE_REGISTRY
from adb_auto_player.util import Execute

from ._base import _GameBase


class _TaskMixin(_GameBase):
    """Mixin that drives custom-routine execution and task-level error handling."""

    def _get_custom_routine_settings(self, name: str) -> TaskListSettings:
        if hasattr(self.settings, name):
            attribute = getattr(self.settings, name)
            if isinstance(attribute, TaskListSettings):
                return attribute
            raise ValueError(f"Attribute '{name}' exists but is not TaskListSettings")
        raise AttributeError(f"Settings has no attribute '{name}'")

    def _execute_custom_routine(self, settings: TaskListSettings) -> None:
        game_commands = self._get_game_commands()
        if not game_commands:
            logging.error("Failed to load Custom Routine Tasks.")
            return

        custom_routines: dict[str, CustomRoutineEntry] = {}
        for task in settings.tasks:
            routine = self._get_custom_routine_for_task(task, game_commands)
            if not routine:
                logging.error(f"Task '{task}' not found")
            else:
                custom_routines[task] = routine

        if not custom_routines:
            logging.error("No Tasks found")
            return

        self._execute_tasks(custom_routines)
        while settings.repeat:
            self._execute_tasks(custom_routines)

    def _get_game_commands(self) -> dict[str, CustomRoutineEntry] | None:
        for module, cmds in CUSTOM_ROUTINE_REGISTRY.items():
            if module in self.__module__:
                return cmds
        return None

    def _get_custom_routine_for_task(
        self, task: str, game_commands: dict[str, CustomRoutineEntry]
    ) -> CustomRoutineEntry | None:
        return game_commands.get(task)

    def _execute_tasks(self, tasks: dict[str, CustomRoutineEntry]) -> None:
        all_tasks_failed = True

        for task, routine in tasks.items():
            error = Execute.function(
                callable_function=routine.func,
                kwargs=routine.kwargs,
            )
            self._handle_task_error(task, error)
            if not error:
                all_tasks_failed = False

        if all_tasks_failed:
            self.restart_game()

    def _handle_task_error(self, task: str, error: Exception | None) -> None:
        if not error:
            return

        if isinstance(error, KeyboardInterrupt):
            raise KeyboardInterrupt

        if isinstance(error, cv2.error):
            if self._stream:
                logging.error(
                    "CV2 error attempting to clear caches and stopping device "
                    f"streaming, original error message: {error}"
                )
                self._stream.stop()
            else:
                logging.error(
                    "CV2 error attempting to clear caches, original error message: "
                    f"{error}"
                )
            IO.cache_clear()
            return

        if isinstance(error, AutoPlayerUnrecoverableError):
            logging.error(
                f"Task '{task}' failed with critical error: {error}, exiting..."
            )
            sys.exit(1)

        if isinstance(error, GameNotRunningOrFrozenError):
            logging.warning(
                f"Task '{task}' failed because the game crashed or is frozen, "
                "attempting to restart it."
            )
            self.restart_game()
            return

        if isinstance(error, AutoPlayerError):
            if not self.is_game_running():
                logging.warning(
                    f"Task '{task}' failed because the game crashed, "
                    "attempting to restart it."
                )
                self.start_game()
            else:
                logging.warning(f"Task '{task}' failed moving to next Task.")
            return

        logging.error(
            f"Task '{task}' failed with unexpected Error: {error} moving to next Task."
        )
