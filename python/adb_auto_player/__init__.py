"""ADB Auto Player Package."""

from .device_stream import DeviceStream, StreamingNotSupportedError
from .game import Game, TemplateMatchParams

__all__: list[str] = [
    "DeviceStream",
    "Game",
    "StreamingNotSupportedError",
    "TemplateMatchParams",
]
