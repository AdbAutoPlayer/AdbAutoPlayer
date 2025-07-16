"""Websocket Server for IPC."""

import asyncio
import json
import logging
import sys
from multiprocessing import Process

from adb_auto_player.ipc import WebsocketMessage
from adb_auto_player.models.commands import Command
from adb_auto_player.util import Execute
from websockets.asyncio.server import ServerConnection, serve


class TaskManager:
    """Manages running tasks and processes."""

    def __init__(self):
        """Init."""
        self.task_process: Process | None = None
        self.running_task: asyncio.Task | None = None

    def is_task_running(self) -> bool:
        """Check if a task is currently running."""
        return self.task_process is not None and self.task_process.is_alive()

    def stop_task(self) -> None:
        """Stop the current task if running."""
        if self.task_process and self.task_process.is_alive():
            self.task_process.terminate()
            self.task_process.join()
        self.task_process = None
        self.running_task = None

    def start_task(self, target, args) -> None:
        """Start a new task."""
        if self.is_task_running():
            return  # Don't start if already running

        self.task_process = Process(target=target, args=args)
        self.task_process.start()


async def monitor_process(
    proc: Process, websocket: ServerConnection, task_manager: TaskManager
):
    """Monitor a process and see if it is running."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, proc.join, None)
    task_manager.task_process = None
    task_manager.running_task = None
    await websocket.close()


def handle_start_message(args: list[str], cmds: dict[str, list[Command]]) -> None:
    """Start Task."""
    Execute.find_command_and_execute(args[0], cmds)


async def handle_connection(
    websocket: ServerConnection,
    cmds: dict[str, list[Command]],
    task_manager: TaskManager,
):
    """Handles incoming messages."""
    async for raw_message in websocket:
        try:
            data = json.loads(raw_message)
            msg: WebsocketMessage = WebsocketMessage(**data)
        except (json.JSONDecodeError, TypeError):
            logging.error("WebSocket Message: Invalid JSON format")
            continue
        except TypeError as e:
            logging.error(f"WebSocket Message: Missing or invalid fields: {e!s}")
            continue

        if msg.command == "stop":
            task_manager.stop_task()
            if msg.notify:
                await websocket.send(json.dumps({"status": "stopped"}))
            await websocket.close()
            return

        if msg.command == "start" and not task_manager.is_task_running():
            task_manager.start_task(target=handle_start_message, args=(msg.args, cmds))
            if task_manager.task_process is None:
                continue
            task_manager.running_task = asyncio.create_task(
                monitor_process(task_manager.task_process, websocket, task_manager)
            )


async def main(host: str, port: int, cmds: dict[str, list[Command]]):
    """Server main function."""
    task_manager = TaskManager()

    async def connection_handler(websocket: ServerConnection):
        await handle_connection(websocket, cmds, task_manager)

    async with serve(connection_handler, host, port, max_queue=1) as server:
        await server.serve_forever()


def start_server(ws_port: int, cmds: dict[str, list[Command]]) -> None:
    """Start server for IPC."""
    try:
        asyncio.run(main(host="localhost", port=ws_port, cmds=cmds))
    except Exception as e:
        print(f"Error in start_server: {e!s}")
        sys.exit(1)
