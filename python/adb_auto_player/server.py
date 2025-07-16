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

task_processes: dict[str, Process] = {}
running_tasks: dict[str, asyncio.Task] = {}


async def monitor_process(proc: Process, websocket, socket_id: str):
    """Monitor a process and see if it is running."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, proc.join, None)
    task_processes.pop(socket_id, None)
    running_tasks.clear()
    await websocket.close()


def handle_start_message(args: list[str], cmds: dict[str, list[Command]]) -> None:
    """Start Task."""
    Execute.find_command_and_execute(args[0], cmds)


async def handle_connection(
    websocket: ServerConnection, cmds: dict[str, list[Command]]
):
    """Handles incoming messages."""
    socket_id = str(websocket.id)

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
            proc = task_processes.get(socket_id)
            if proc and proc.is_alive():
                proc.terminate()
                proc.join()
                if msg.notify:
                    await websocket.send(json.dumps({"status": "stopped"}))
            _ = task_processes.pop(socket_id, None)
            await websocket.close()
            return

        if msg.command == "start" and (
            socket_id not in task_processes or not task_processes[socket_id].is_alive()
        ):
            proc = Process(target=handle_start_message, args=(msg.args, cmds))
            task_processes[socket_id] = proc
            proc.start()
            running_tasks[socket_id] = asyncio.create_task(
                monitor_process(proc, websocket, socket_id)
            )


async def main(host: str, port: int, cmds: dict[str, list[Command]]):
    """Server main function."""

    async def connection_handler(websocket: ServerConnection):
        await handle_connection(websocket, cmds)

    async with serve(connection_handler, host, port, max_queue=1) as server:
        await server.serve_forever()


def start_server(ws_port: int, cmds: dict[str, list[Command]]) -> None:
    """Start server for IPC."""
    try:
        asyncio.run(main(host="localhost", port=ws_port, cmds=cmds))
    except Exception as e:
        print(f"Error in start_server: {e!s}")
        sys.exit(1)
