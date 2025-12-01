"""The main entry point for the Tauri app."""

import asyncio
import logging
import multiprocessing
import sys
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from datetime import datetime
from functools import wraps
from logging.handlers import QueueHandler, QueueListener
from multiprocessing import Process, Queue, freeze_support
from os import getenv
from pathlib import Path
from typing import Any, Literal, NoReturn

from adb_auto_player.commands import log_debug_info
from adb_auto_player.device.adb import AdbController
from adb_auto_player.file_loader import SettingsLoader
from adb_auto_player.ipc import GameGUIOptions, LogMessage
from adb_auto_player.log import LogPreset
from adb_auto_player.models.decorators import CacheGroup
from adb_auto_player.models.pydantic.app_settings import AppSettings
from adb_auto_player.models.registries import GameMetadata
from adb_auto_player.registries import CACHE_REGISTRY, CUSTOM_ROUTINE_REGISTRY
from adb_auto_player.task_loader import get_game_tasks
from adb_auto_player.tauri_context import TauriContext
from adb_auto_player.tauri_helpers import get_game_gui_options, get_game_metadata
from adb_auto_player.util import (
    Execute,
    LogMessageFactory,
    RuntimeInfo,
    StringHelper,
    SummaryGenerator,
)
from anyio.from_thread import start_blocking_portal
from pydantic import BaseModel
from pytauri import (
    AppHandle,
    Commands,
    Emitter,
    Event,
    Listener,
    Manager,
    builder_factory,
    context_factory,
)

PYTAURI_GEN_TS = getenv("VIRTUAL_ENV_PROMPT") == "AdbAutoPlayer"
commands: Commands = Commands(experimental_gen_ts=PYTAURI_GEN_TS)

task_processes: dict[int, Process | None] = {}
task_listeners: dict[int, QueueListener | None] = {}
task_labels: dict[int, str | None] = {}
task_summary_queues: dict[int, Queue | None] = {}

_base_app_config_dir: Path | None = None
_base_resource_dir: Path | None = None

profile_state_locks: dict[int, asyncio.Lock] = {}
_executor = ThreadPoolExecutor(max_workers=4)


class ProfileContext(BaseModel):
    profile_index: int


def tauri_profile_aware_command(func):
    """Combines @commands.command() and context handling.

    The decorated function should have `app_handle: AppHandle` as the first argument.
    """

    @wraps(func)
    async def wrapper(app_handle: AppHandle, body: ProfileContext, *args, **kwargs):
        global _base_app_config_dir, _base_resource_dir
        TauriContext.set_app_handle(app_handle)
        if not isinstance(body, ProfileContext):
            raise RuntimeError("body must be of type ProfileContext")
        TauriContext.set_profile_index(body.profile_index)
        if not _base_app_config_dir:
            _base_app_config_dir = Manager.path(app_handle).app_config_dir()

        if not _base_resource_dir:
            _base_resource_dir = Manager.path(app_handle).resource_dir()
            # Tauri Dev
            if _base_resource_dir.parts[-3:] == ("AdbAutoPlayer", "target", "debug"):
                _base_resource_dir = (
                    _base_resource_dir.parent.parent
                    / "src-tauri"
                    / "src-python"
                    / "adb_auto_player"
                )

        SettingsLoader.set_app_config_dir(
            _base_app_config_dir / f"{body.profile_index}"
        )
        SettingsLoader.set_resource_dir(_base_resource_dir)
        try:
            return await func(app_handle, body, *args, **kwargs)
        finally:
            TauriContext.set_app_handle(None)

    commands.command()(wrapper)
    return wrapper


class TauriQueueHandler(logging.Handler):
    def __init__(self, app_handle, profile_index):
        super().__init__()
        self.app_handle = app_handle
        self.profile_index = profile_index

    def emit(self, record):
        log_message = LogMessageFactory.create_log_message(
            record=record,
            message=StringHelper.sanitize_path(record.getMessage()),
            html_class=getattr(record, "preset", None),
            profile_index=self.profile_index,
        )
        Emitter.emit(self.app_handle, "log-message", log_message)


def _setup_logging() -> None:
    class TauriLogHandler(logging.Handler):
        """Log handler that emits log messages to Tauri."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def emit(self, record: logging.LogRecord) -> None:
            """Store log message in memory.

            Args:
                record (logging.LogRecord): The log record to store.
            """
            preset: LogPreset | None = getattr(record, "preset", None)

            log_message: LogMessage = LogMessageFactory.create_log_message(
                record=record,
                message=StringHelper.sanitize_path(record.getMessage()),
                html_class=preset.get_html_class() if preset else None,
                profile_index=TauriContext.get_profile_index(),
            )
            app_handle = TauriContext.get_app_handle()
            if app_handle:
                Emitter.emit(app_handle, "log-message", log_message)
            else:
                print(f"[ERROR] No AppHandle in current context: {record.getMessage()}")

    logger: logging.Logger = logging.getLogger()
    for handler in logger.handlers:
        logger.removeHandler(handler)
    logger.addHandler(TauriLogHandler())
    logger.setLevel(logging.DEBUG)


def run_task(
    command: str,
    log_queue: Queue,
    summary_queue: Queue,
    app_config_dir: Path,
    resource_dir: Path,
) -> None:
    """Wrapper to run task in a separate process."""
    queue_handler = QueueHandler(log_queue)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(queue_handler)

    def summary_callback(msg: str | None):
        try:
            summary_queue.put(msg)
        except Exception:
            pass

    SummaryGenerator.set_callback(summary_callback)
    SettingsLoader.set_app_config_dir(app_config_dir)
    SettingsLoader.set_resource_dir(resource_dir)

    try:
        e = Execute.find_command_and_execute(command, get_game_tasks())
        if isinstance(e, BaseException):
            logging.error(e, exc_info=True)
            sys.exit(1)
    except Exception as exc:
        logging.error(exc, exc_info=True)
        sys.exit(1)


class StartTaskBody(ProfileContext):
    args: list[str]
    label: str


class SummaryEvent(BaseModel):
    profile_index: int
    msg: str | None


@tauri_profile_aware_command
async def start_task(
    app_handle: AppHandle,
    body: StartTaskBody,
) -> None:
    if not _base_app_config_dir:
        logging.error("Cannot resolve App Config Dir")
        return

    task_process = task_processes.get(body.profile_index, None)

    if task_process and task_process.is_alive():
        logging.warning("Task is already running!")
        return

    log_queue = Queue()
    summary_queue = Queue()
    task_summary_queues[body.profile_index] = summary_queue

    listener = QueueListener(
        log_queue, TauriQueueHandler(app_handle, body.profile_index)
    )
    task_listeners[body.profile_index] = listener
    listener.start()

    task_process = Process(
        target=run_task,
        args=(
            " ".join(body.args),
            log_queue,
            summary_queue,
            _base_app_config_dir / f"{body.profile_index}",
            _base_resource_dir,
        ),
    )

    task_processes[body.profile_index] = task_process
    task_labels[body.profile_index] = body.label
    task_process.start()

    while task_process and task_process.is_alive():
        await asyncio.sleep(0.5)

    task_processes[body.profile_index] = None
    task_labels[body.profile_index] = None

    listener = task_listeners.get(body.profile_index, None)
    if listener:
        listener.stop()
        task_listeners[body.profile_index] = None

    # Get summary from queue
    summary_msg = None
    if not summary_queue.empty():
        try:
            summary_msg = summary_queue.get_nowait()
        except Exception:
            pass

    task_summary_queues[body.profile_index] = None

    Emitter.emit(
        app_handle,
        "write-summary-to-log",
        SummaryEvent(
            profile_index=body.profile_index, msg=summary_msg
        ),
    )


@tauri_profile_aware_command
async def stop_task(
    app_handle: AppHandle,
    body: ProfileContext,
) -> None:
    task_process = task_processes.get(body.profile_index, None)
    if task_process and task_process.is_alive():
        logging.info("Stopping Task")
        task_process.terminate()
        task_process.join()
        await asyncio.sleep(0.5)  # wait a bit for start_task tear down


class CacheClear(ProfileContext):
    trigger: Literal["adb-settings-updated", "game-settings-updated"]


def _cache_clear(
    group: CacheGroup,
    profile_index: int | None = None,
) -> None:
    """Clear cache for a specific group."""
    for func, profile_aware in CACHE_REGISTRY.get(group, []):
        if cache_clear_func := getattr(func, "cache_clear", None):
            if profile_aware and profile_index is not None:
                cache_clear_func(profile_index)
            else:
                cache_clear_func()


@tauri_profile_aware_command
async def debug(
    app_handle: AppHandle,
    body: ProfileContext,
) -> None:
    for group in CacheGroup:
        _cache_clear(group, body.profile_index)
    log_debug_info()


@tauri_profile_aware_command
async def get_adb_settings_form(
    app_handle: AppHandle,
    body: ProfileContext,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    settings = SettingsLoader.adb_settings()
    return (
        settings.model_dump(by_alias=True),
        settings.model_json_schema(),
        "ADB.toml",
    )


@tauri_profile_aware_command
async def get_game_settings_form(
    app_handle: AppHandle,
    body: ProfileContext,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    metadata: GameMetadata | None = get_game_metadata()
    if (
        not metadata
        or not metadata.settings_file
        or not metadata.gui_metadata
        or not metadata.gui_metadata.settings_class
    ):
        raise Exception("gg you managed to run into a race condition")
    path = SettingsLoader.settings_dir() / metadata.settings_file
    settings = metadata.gui_metadata.settings_class.from_toml(path)

    module = StringHelper.get_game_module(settings.__module__)
    choices = list(CUSTOM_ROUTINE_REGISTRY.get(module, {}).keys())

    schema = settings.model_json_schema()
    defs = schema.setdefault("$defs", {})
    if "TaskListSettings" in defs and "properties" in defs["TaskListSettings"]:
        defs["TaskListSettings"]["properties"]["Task List"]["items"] = {
            "$ref": "#/$defs/TaskListEnum"
        }

        defs["TaskListEnum"] = {
            "title": "TaskListEnum",
            "type": "string",
            "enum": choices,
        }

    return settings.model_dump(by_alias=True), schema, str(metadata.settings_file)


class ProfileState(BaseModel):
    game_menu: GameGUIOptions | None
    device_id: str | None
    active_task: str | None


class ProfileStateUpdate(BaseModel):
    state: ProfileState
    timestamp: float
    index: int


def get_profile_state_lock(index: int) -> asyncio.Lock:
    if index not in profile_state_locks:
        profile_state_locks[index] = asyncio.Lock()
    return profile_state_locks[index]


def _get_state_sync(profile_index: int) -> ProfileState:
    """Synchronous helper function that runs in thread pool.

    Context variables are already set by copy_context().
    """
    try:
        state = ProfileState(
            game_menu=get_game_gui_options(),
            device_id=AdbController().d.serial,
            active_task=task_labels.get(profile_index, None),
        )
    except Exception as e:
        _cache_clear(CacheGroup.ADB, profile_index)
        logging.error(e)
        state = ProfileState(
            game_menu=None,
            device_id=None,
            active_task=task_labels.get(profile_index, None),
        )
    return state


@tauri_profile_aware_command
async def get_profile_state(
    app_handle: AppHandle,
    body: ProfileContext,
) -> None:
    lock = get_profile_state_lock(body.profile_index)

    # if already running, skip completely to prevent race conditions
    if lock.locked():
        return

    # convert to ms for FE
    timestamp = int(datetime.now().timestamp() * 1000)

    async with lock:
        ctx = copy_context()
        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(
            _executor,
            lambda: ctx.run(_get_state_sync, body.profile_index),
        )

        Emitter.emit(
            app_handle,
            "profile-state-update",
            ProfileStateUpdate(
                state=state,
                index=body.profile_index,
                timestamp=timestamp,
            ),
        )
    return


@tauri_profile_aware_command
async def cache_clear(
    app_handle: AppHandle,
    body: CacheClear,
) -> None:
    if body.trigger == "adb-settings-updated":
        _cache_clear(CacheGroup.ADB_SETTINGS, body.profile_index)
        _cache_clear(CacheGroup.ADB, body.profile_index)

    _cache_clear(CacheGroup.GAME_SETTINGS, body.profile_index)


def _model_gen_command_error() -> NoReturn:
    raise RuntimeError(
        "This function exists to generate TypeScript bindings and should not be called."
    )


@commands.command()
async def _generate_app_settings_model() -> AppSettings:
    _model_gen_command_error()


@commands.command()
async def _generate_profile_state_update_model() -> ProfileStateUpdate:
    _model_gen_command_error()


def main() -> int:
    """PyTauri main."""
    _setup_logging()

    with start_blocking_portal("asyncio") as portal:
        if PYTAURI_GEN_TS:
            output_dir = Path(__file__).parent.parent.parent.parent / "src" / "client"
            json2ts_cmd = "pnpm json2ts --format=false"

            portal.start_task_soon(
                lambda: commands.experimental_gen_ts_background(output_dir, json2ts_cmd)
            )
        app = builder_factory().build(
            context=context_factory(),
            invoke_handler=commands.generate_handler(portal),
        )

        def handler(event: Event):
            for process in task_processes.values():
                if process and process.is_alive():
                    process.terminate()
                    process.join()
            _executor.shutdown(wait=False, cancel_futures=True)
            sys.exit(0)

        Listener.listen(app, "kill-python", handler)

        exit_code = app.run_return()
        return exit_code


if RuntimeInfo.is_mac():
    multiprocessing.set_start_method(
        "spawn",
        force=True,
    )


if __name__ == "__main__":
    # - If you don't use `multiprocessing`, you can remove this line.
    # - If you do use `multiprocessing` but without this line,
    #   you will get endless spawn loop of your application process.
    #   See: <https://pyinstaller.org/en/v6.11.1/common-issues-and-pitfalls.html#multi-processing>.
    freeze_support()
    sys.exit(main())