"""Websocket ipc stuff."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WebsocketMessage:
    """Websocket Message for IPC."""

    command: str
    args: list[str]
    notify: bool | None = None
