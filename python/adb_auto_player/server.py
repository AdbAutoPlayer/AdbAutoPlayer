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
from adb_auto_player.util import Execute, LogMessageFactory, StringHelper
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

    def __init__(self, log_queue: Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        """Convert log record to LogMessage and send to queue."""
        try:
            preset: LogPreset | None = getattr(record, "preset", None)

            log_message: LogMessage = LogMessageFactory.create_log_message(
                record=record,
                message=StringHelper.sanitize_path(record.getMessage()),
                html_class=preset.get_html_class() if preset else None,
            )

            self.log_queue.put(log_message.to_dict())
        except Exception as e:
            print(f"Failed to send log to queue: {e}")


def run_command_in_process(command: list[str], commands_dict: dict, log_queue: Queue):
    """Function to run a command in a separate process.

    This function will be executed in the child process.
    """
    try:
        logger = logging.getLogger()

        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        queue_handler = ProcessLogHandler(log_queue)
        queue_handler.setLevel(logging.DEBUG)
        logger.addHandler(queue_handler)
        logger.setLevel(logging.DEBUG)

        parser = ArgparseHelper.build_argument_parser(
            commands_dict, exit_on_error=False
        )
        args = parser.parse_args(command)

        if not Execute.find_command_and_execute(args.command, commands_dict):
            logging.error(f"Unrecognized command: {command}")
            log_queue.put(None)
            return False

        log_queue.put(None)
        return True

    except argparse.ArgumentError as e:
        logging.error(f"Unrecognized command: {e}")
        log_queue.put(None)
        return False
    except Exception as e:
        logging.error(f"Execution error: {e!s}")
        log_queue.put(None)
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
        self.current_process: Process | None = None
        self.current_log_queue: Queue | None = None
        self.log_reader_task: asyncio.Task | None = None
        self.command_execution_task: asyncio.Task | None = None

        # Setup logging
        self._setup_logging()
        self._setup_middleware()
        self._setup_tcp_routes()
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
    async def _read_log_queue(log_queue: Queue):
        """Read LogMessage objects from the queue and forward them to WebSocket."""
        while True:
            try:
                # Use a small timeout to make this cancellable
                await asyncio.sleep(0.01)

                if not log_queue.empty():
                    try:
                        log_data = log_queue.get_nowait()

                        if log_data is None:
                            break

                        websocket = current_websocket.get()
                        if (
                            websocket
                            and websocket.client_state == WebSocketState.CONNECTED
                        ):
                            await websocket.send_text(json.dumps(log_data))

                    except Exception as e:
                        print(f"Error processing log message: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in log queue reader: {e}")
                await asyncio.sleep(0.1)

    async def _execute_command_background(self, command: list[str]) -> None:
        """Execute command in background process."""
        try:
            self.current_log_queue = Queue()

            self.current_process = Process(
                target=run_command_in_process,
                args=(command, self.commands, self.current_log_queue),
            )
            self.current_process.start()

            self.log_reader_task = asyncio.create_task(
                FastAPIServer._read_log_queue(self.current_log_queue)
            )

            while self.current_process.is_alive():
                await asyncio.sleep(0.1)

            if self.log_reader_task and not self.log_reader_task.done():
                try:
                    await asyncio.wait_for(self.log_reader_task, timeout=1.0)
                except TimeoutError:
                    self.log_reader_task.cancel()

        except asyncio.CancelledError:
            await self._stop_current_command()
            raise
        finally:
            if self.current_process and self.current_process.is_alive():
                self.current_process.terminate()
                self.current_process.join(timeout=5)
                if self.current_process.is_alive():
                    self.current_process.kill()

            self.current_process = None
            self.current_log_queue = None

            if self.log_reader_task and not self.log_reader_task.done():
                self.log_reader_task.cancel()
            self.log_reader_task = None

    async def _stop_current_command(self) -> None:
        """Stop the currently running command process."""
        if self.command_execution_task and not self.command_execution_task.done():
            self.command_execution_task.cancel()
            try:
                await self.command_execution_task
            except asyncio.CancelledError:
                pass
            self.command_execution_task = None

        if self.current_process and self.current_process.is_alive():
            try:
                self.current_process.terminate()
                # Wait a bit for graceful shutdown
                await asyncio.sleep(0.5)
                if self.current_process.is_alive():
                    self.current_process.kill()
                self.current_process.join(timeout=2)
            except Exception as e:
                logging.error(f"Error stopping command: {e}")

        if self.log_reader_task and not self.log_reader_task.done():
            self.log_reader_task.cancel()
            try:
                await self.log_reader_task
            except asyncio.CancelledError:
                pass

    async def _handle_websocket_stop(self) -> None:
        """Handle stop request via WebSocket."""
        await self._stop_current_command()

    def _setup_websocket_routes(self):
        """Set up websocket routes."""

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time command execution and logging."""
            await websocket.accept()
            current_websocket.set(websocket)

            try:
                while True:
                    try:
                        data = await websocket.receive_text()
                        message = json.loads(data)

                        if message.get("type") == "execute_command":
                            command = message.get("command", [])
                            if not command:
                                continue

                            await self._stop_current_command()

                            self.command_execution_task = asyncio.create_task(
                                self._execute_command_background(command)
                            )
                        elif message.get("type") == "stop":
                            await self._handle_websocket_stop()

                    except WebSocketDisconnect:
                        break
                    except Exception as e:
                        logging.error(f"WebSocket error: {e}")
            except WebSocketDisconnect:
                pass
            finally:
                # Clean up on disconnect
                await self._stop_current_command()
                current_websocket.set(None)

    def _setup_tcp_routes(self):
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

                if Execute.find_command_and_execute(args.command, self.commands):
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
