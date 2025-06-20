"""ADB Auto Player Package."""

from .command import Command
from .config.game_config_base import ConfigBase
from .config_loader import ConfigLoader
from .device_stream import DeviceStream, StreamingNotSupportedError
from .exceptions import (
    AutoPlayerError,
    AutoPlayerUnrecoverableError,
    AutoPlayerWarningError,
    GameActionFailedError,
    GameNotRunningOrFrozenError,
    GameStartError,
    GameTimeoutError,
    GenericAdbError,
    GenericAdbUnrecoverableError,
    NotInitializedError,
    UnsupportedResolutionError,
)
from .game import Game, TapParams, TemplateMatchParams

__all__: list[str] = [
    "AutoPlayerError",
    "AutoPlayerUnrecoverableError",
    "AutoPlayerWarningError",
    "Command",
    "ConfigBase",
    "ConfigLoader",
    "DeviceStream",
    "Game",
    "GameActionFailedError",
    "GameNotRunningOrFrozenError",
    "GameStartError",
    "GameTimeoutError",
    "GenericAdbError",
    "GenericAdbUnrecoverableError",
    "NotInitializedError",
    "StreamingNotSupportedError",
    "TapParams",
    "TemplateMatchParams",
    "UnsupportedResolutionError",
]
