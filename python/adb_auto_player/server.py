"""FastAPI server mode for adb_auto_player."""

import argparse
import logging
from contextvars import ContextVar

from adb_auto_player.cli import ArgparseHelper
from adb_auto_player.ipc import LogMessage
from adb_auto_player.log import MemoryLogHandler
from adb_auto_player.models.commands import Command
from adb_auto_player.models.decorators import CacheGroup
from adb_auto_player.registries import LRU_CACHE_REGISTRY
from adb_auto_player.util import Execute
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from starlette.requests import Request

current_request_handler: ContextVar[MemoryLogHandler | None] = ContextVar(
    "current_request_handler", default=None
)


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


class LogMessageListResponse(BaseModel):
    """Response with list of LogMessages for short tasks."""

    messages: list[LogMessage]


class OKResponse(BaseModel):
    """Simple OK Response."""

    detail: str = "ok"


class FastAPIServer:
    """Server for IPC with GUI."""

    def __init__(
        self,
        commands: dict[str, list[Command]],
    ):
        self.app = FastAPI(title="ADB Auto Player Server")
        self.commands = commands

        context_handler = ContextAwareHandler()
        context_handler.setLevel(logging.DEBUG)
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        logger.addHandler(context_handler)
        logger.setLevel(logging.DEBUG)

        self._setup_middleware()
        self._setup_routes()

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

    def _setup_routes(self):
        """Setup FastAPI routes."""

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

        @self.app.post("/settings/general/updated", response_model=OKResponse)
        async def general_settings_updated():
            """Handle general settings update."""
            self._clear_cache(CacheGroup.GENERAL_SETTINGS)
            self._clear_cache(CacheGroup.ADB)
            return OKResponse()

        @self.app.post("/settings/game/updated", response_model=OKResponse)
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
