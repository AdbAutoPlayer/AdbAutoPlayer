"""FastAPI server mode for adb_auto_player with real-time logging."""

import argparse
import asyncio
import json
import logging
from contextvars import ContextVar
from multiprocessing import Process, Queue

from adb_auto_player.cli import ArgparseHelper
from adb_auto_player.ipc import LogMessage
from adb_auto_player.log import LogPreset, MemoryLogHandler
from adb_auto_player.models.commands import Command
from adb_auto_player.models.decorators import CacheGroup
from adb_auto_player.registries import LRU_CACHE_REGISTRY
from adb_auto_player.util import (
    Execute,
    LogMessageFactory,
    StringHelper,
    SummaryGenerator,
)
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from starlette.requests import Request
from starlette.websockets import WebSocketState

current_websocket: ContextVar[WebSocket | None] = ContextVar(
    "current_websocket", default=None
)

current_request_handler: ContextVar[MemoryLogHandler | None] = ContextVar(
    "current_request_handler", default=None
)


class ProcessLogHandler(logging.Handler):
    """A logging handler that sends LogMessage objects to a queue for ipc."""

    def __init__(self, message_queue):
        super().__init__()
        self.message_queue = message_queue

    def emit(self, record):
        """Convert log record to LogMessage and send to queue."""
        try:
            preset: LogPreset | None = getattr(record, "preset", None)

            log_message: LogMessage = LogMessageFactory.create_log_message(
                record=record,
                message=StringHelper.sanitize_path(record.getMessage()),
                html_class=preset.get_html_class() if preset else None,
            )

            self.message_queue.put(log_message.to_dict())
        except Exception as e:
            print(f"Failed to send log to queue: {e}")


def run_command_in_process(
    command: list[str], commands_dict: dict, message_queue: Queue
):
    """Function to run a command in a separate process.

    This function will be executed in the child process.
    """
    try:
        logger = logging.getLogger()

        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        queue_handler = ProcessLogHandler(message_queue)
        queue_handler.setLevel(logging.DEBUG)
        logger.addHandler(queue_handler)
        logger.setLevel(logging.DEBUG)
        SummaryGenerator.set_message_queue(message_queue)

        parser = ArgparseHelper.build_argument_parser(
            commands_dict, exit_on_error=False
        )
        args = parser.parse_args(command)

        result = Execute.find_command_and_execute(args.command, commands_dict)
        if isinstance(result, Exception):
            logging.error(f"Task ended with Error: {result}")
        if not result:
            logging.error(f"Unrecognized command: {command}")
            message_queue.put(None)
            return False

        message_queue.put(None)
        return True

    except argparse.ArgumentError as e:
        logging.error(f"Unrecognized command: {e}")
        message_queue.put(None)
        return False
    except Exception as e:
        logging.error(f"Execution error: {e!s}")
        message_queue.put(None)
        return False


class WebSocketLogHandler(logging.Handler):
    """A logging handler that sends messages directly via WebSocket."""

    def __init__(self):
        super().__init__()
        self._background_tasks = set()

    def emit(self, record):
        """Send log messages via WebSocket if available."""
        websocket = current_websocket.get()
        if websocket and websocket.client_state == WebSocketState.CONNECTED:
            try:
                preset: LogPreset | None = getattr(record, "preset", None)

                log_message: LogMessage = LogMessageFactory.create_log_message(
                    record=record,
                    message=StringHelper.sanitize_path(record.getMessage()),
                    html_class=preset.get_html_class() if preset else None,
                )

                task = asyncio.create_task(
                    self._send_log_message(websocket, log_message)
                )
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
            except Exception as e:
                print(f"Failed to send log via WebSocket: {e}")

    @staticmethod
    async def _send_log_message(websocket: WebSocket, log_message: LogMessage):
        """Send log message via WebSocket."""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                message_data = log_message.to_dict()
                await websocket.send_text(json.dumps(message_data))
        except Exception as e:
            print(f"Error sending WebSocket message: {e}")


class ContextAwareHandler(logging.Handler):
    """A logging handler that routes messages to the current request's handler."""

    def emit(self, record):
        """Only emits for current request's handler."""
        request_handler = current_request_handler.get()
        if request_handler:
            request_handler.emit(record)


class CommandRequest(BaseModel):
    """Request body to execute a command."""

    command: list[str]


class WebSocketCommandRequest(BaseModel):
    """WebSocket command request."""

    type: str = "execute_command"
    command: list[str]


class WebSocketStopRequest(BaseModel):
    """WebSocket stop request."""

    type: str = "stop"


class LogMessageListResponse(BaseModel):
    """Response with list of LogMessages for short tasks."""

    messages: list[LogMessage]


class OKResponse(BaseModel):
    """Simple OK Response."""

    detail: str = "ok"


class FastAPIServer:
    """Server for IPC with GUI supporting both HTTP and WebSocket."""

    def __init__(
        self,
        commands: dict[str, list[Command]],
    ):
        self.app = FastAPI(title="ADB Auto Player Server")
        self.commands = commands
        self.websocket_handler = WebSocketLogHandler()

        self._setup_logging()
        self._setup_middleware()
        self._setup_http_routes()
        self._setup_websocket_routes()

    def _setup_logging(self):
        """Setup logging handlers."""
        context_handler = ContextAwareHandler()
        context_handler.setLevel(logging.DEBUG)

        self.websocket_handler.setLevel(logging.DEBUG)

        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        logger.addHandler(context_handler)
        logger.addHandler(self.websocket_handler)
        logger.setLevel(logging.DEBUG)

    def _setup_middleware(self):
        @self.app.middleware("http")
        async def logging_middleware(request: Request, call_next):
            """Middleware that sets up request-specific logging context."""
            request_handler = MemoryLogHandler()
            request_handler.setLevel(logging.DEBUG)
            current_request_handler.set(request_handler)
            try:
                response = await call_next(request)
                return response
            finally:
                request_handler.clear()
                current_request_handler.set(None)

    @staticmethod
    async def _read_message_queue(message_queue: Queue, shutdown_event: asyncio.Event):
        """Read json messages from the queue and forward them to WebSocket."""
        while not shutdown_event.is_set():
            try:
                await asyncio.sleep(0.01)

                if not message_queue.empty():
                    try:
                        log_data = message_queue.get_nowait()

                        if log_data is None:
                            break

                        websocket = current_websocket.get()
                        if (
                            websocket
                            and websocket.client_state == WebSocketState.CONNECTED
                        ):
                            try:
                                await asyncio.wait_for(
                                    websocket.send_text(json.dumps(log_data)),
                                    timeout=1.0,
                                )
                            except Exception as e:
                                logging.warning(f"WebSocket send failed: {e}")
                                break

                    except Exception as e:
                        logging.error(f"Error processing log message: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error in log queue reader: {e}")
                await asyncio.sleep(0.1)

    async def _execute_command_background(self, command: list[str]) -> None:
        """Execute command in background process."""
        process = None
        log_reader_task = None
        message_queue: Queue = Queue()

        try:
            shutdown_event = asyncio.Event()

            process = Process(
                target=run_command_in_process,
                args=(command, self.commands, message_queue),
            )
            process.start()

            log_reader_task = asyncio.create_task(
                self._read_message_queue(message_queue, shutdown_event)
            )

            while process.is_alive():
                try:
                    await asyncio.wait_for(asyncio.sleep(0.1), timeout=0.1)
                except TimeoutError:
                    continue

            shutdown_event.set()

            if log_reader_task and not log_reader_task.done():
                try:
                    await asyncio.wait_for(log_reader_task, timeout=2.0)
                except TimeoutError:
                    logging.warning("Log reader task timeout during cleanup")
                    log_reader_task.cancel()

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error(f"Error in command execution: {e}")
        finally:
            await FastAPIServer._cleanup_process_and_tasks(
                process,
                log_reader_task,
                message_queue,
            )

    @staticmethod
    async def _cleanup_process_and_tasks(
        process: Process | None,
        log_reader_task: asyncio.Task | None,
        message_queue: Queue,
    ):
        """Comprehensive cleanup of process and associated tasks."""
        if log_reader_task and not log_reader_task.done():
            log_reader_task.cancel()
            try:
                await asyncio.wait_for(log_reader_task, timeout=1.0)
            except (TimeoutError, asyncio.CancelledError):
                pass

        if process and process.is_alive():
            try:
                process.terminate()

                for _ in range(10):
                    if not process.is_alive():
                        break
                    await asyncio.sleep(0.1)

                if process.is_alive():
                    process.kill()

                try:
                    process.join(timeout=2)
                except Exception as e:
                    logging.error(f"Error joining process: {e}")

            except Exception as e:
                logging.error(f"Error during process cleanup: {e}")

        if message_queue:
            try:
                while not message_queue.empty():
                    message_queue.get_nowait()
            except Exception:
                pass

    def _setup_websocket_routes(self):  # noqa: PLR0915
        """Set up websocket routes with improved error handling."""

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):  # noqa: PLR0915
            """WebSocket endpoint for real-time command execution and logging."""
            await websocket.accept()
            current_websocket.set(websocket)

            # Track the current task for this specific WebSocket connection
            current_task = None

            async def stop_current_task():
                """Stop the current task for this WebSocket connection."""
                nonlocal current_task
                if current_task and not current_task.done():
                    current_task.cancel()
                    try:
                        await asyncio.wait_for(current_task, timeout=3.0)
                    except (TimeoutError, asyncio.CancelledError):
                        pass
                    finally:
                        current_task = None

            def on_command_done(task: asyncio.Task):
                async def close_ws():
                    try:
                        await websocket.close(reason="Task completed")
                    except Exception as e:
                        logging.error(f"Error closing websocket: {e}")

                close_task = asyncio.create_task(close_ws())
                close_task.add_done_callback(lambda t: None)

            try:
                while True:
                    try:
                        data = await asyncio.wait_for(
                            websocket.receive_text(), timeout=5.0
                        )
                        message = json.loads(data)

                        if message.get("type") == "execute_command":
                            command = message.get("command", [])
                            if not command:
                                continue

                            await stop_current_task()

                            current_task = asyncio.create_task(
                                self._execute_command_background(command)
                            )
                            current_task.add_done_callback(on_command_done)

                        elif message.get("type") == "stop":
                            await stop_current_task()

                    except TimeoutError:
                        # Ping/pong could be implemented here
                        continue
                    except WebSocketDisconnect:
                        break
                    except json.JSONDecodeError:
                        logging.warning("Invalid JSON received via WebSocket")
                        continue
                    except Exception as e:
                        logging.error(f"WebSocket message handling error: {e}")
                        break

            except WebSocketDisconnect:
                pass
            except Exception as e:
                logging.error(f"WebSocket error: {e}")

            await stop_current_task()
            current_websocket.set(None)

            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.close()
            except Exception as e:
                logging.error(f"Error closing WebSocket: {e}")

    def _setup_http_routes(self):
        """Setup TCP routes."""

        @self.app.post("/execute", response_model=LogMessageListResponse)
        async def execute_command(request: CommandRequest):
            """Execute a single command via HTTP/TCP."""
            handler = current_request_handler.get()
            if not handler:
                raise RuntimeError("No request handler found in context")
            handler.clear()

            try:
                parser = ArgparseHelper.build_argument_parser(
                    self.commands, exit_on_error=False
                )

                command = request.command
                args = parser.parse_args(command)

                result = Execute.find_command_and_execute(args.command, self.commands)
                if isinstance(result, Exception):
                    logging.error(f"Task ended with Error: {result}")
                if result:
                    return LogMessageListResponse(messages=handler.get_messages())
            except argparse.ArgumentError:
                raise HTTPException(
                    status_code=404, detail=f"Unrecognized command: {request.command}"
                )
            except Exception:
                return LogMessageListResponse(messages=handler.get_messages())
            raise HTTPException(
                status_code=404, detail=f"Unrecognized command: {request.command}"
            )

        @self.app.get("/health", response_model=OKResponse)
        async def health_check():
            """Health check."""
            return OKResponse(detail="ADB Auto Player Server")

        @self.app.post("/general-settings-updated", response_model=OKResponse)
        async def general_settings_updated():
            """Handle general settings update."""
            self._clear_cache(CacheGroup.GENERAL_SETTINGS)
            self._clear_cache(CacheGroup.GAME_SETTINGS)
            self._clear_cache(CacheGroup.ADB)
            return OKResponse()

        @self.app.post("/game-settings-updated", response_model=OKResponse)
        async def game_settings_updated():
            """Handle game settings update."""
            self._clear_cache(CacheGroup.GAME_SETTINGS)
            return OKResponse()

    @staticmethod
    def _clear_cache(group: CacheGroup) -> None:
        """Clear cache for a specific group."""
        for func in LRU_CACHE_REGISTRY.get(group, []):
            if hasattr(func, "cache_clear"):
                func.cache_clear()


def create_fastapi_server(commands: dict[str, list[Command]]) -> FastAPI:
    """Create and configure FastAPI server."""
    server = FastAPIServer(commands)
    return server.app
