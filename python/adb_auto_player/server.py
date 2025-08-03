"""FastAPI server mode for adb_auto_player with real-time logging."""

import argparse
import asyncio
import json
import logging
from contextvars import ContextVar

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

        # Setup logging
        self._setup_logging()
        self._setup_middleware()
        self._setup_routes()

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

    async def _handle_websocket_command(self, message: dict) -> None:
        """Handle command execution via WebSocket."""
        try:
            command = message.get("command", [])
            if not command:
                return

            parser = ArgparseHelper.build_argument_parser(
                self.commands, exit_on_error=False
            )

            args = parser.parse_args(command)

            if not Execute.find_command_and_execute(args.command, self.commands):
                logging.error(f"Unrecognized command: {command}")
        except argparse.ArgumentError as e:
            logging.error(f"Unrecognized command: {e}")
        except Exception as e:
            logging.error(f"Execution error: {e!s}")

    def _setup_routes(self):
        """Setup FastAPI routes."""

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
                            await self._handle_websocket_command(message)
                        elif message.get("type") == "stop":
                            # TODO
                            print("TODO")
                            pass

                    except WebSocketDisconnect:
                        break
                    except Exception as e:
                        logging.error(e)
            except WebSocketDisconnect:
                pass
            finally:
                current_websocket.set(None)

        @self.app.post("/execute", response_model=LogMessageListResponse)
        async def execute_command(request: CommandRequest):
            """Execute a single command via HTTP/TCP (legacy support)."""
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
