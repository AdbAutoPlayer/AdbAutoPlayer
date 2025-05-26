"""ADB Auto Player Package."""

from .command import Command
from .config.game_config_base import ConfigBase
from .config_loader import ConfigLoader
from .device_stream import DeviceStream, StreamingNotSupportedError
from .exceptions import (
    AutoPlayerError,
    AutoPlayerPanicError,
    AutoPlayerWarningError,
    GameTimeoutError,
    GenericAdbError,
    NotInitializedError,
    UnsupportedResolutionError,
)
from .game import Coordinates, Game
from .template_matching import CropRegions, MatchMode

__all__: list[str] = [
    "AutoPlayerError",
    "AutoPlayerPanicError",
    "AutoPlayerWarningError",
    "Command",
    "ConfigBase",
    "ConfigLoader",
    "Coordinates",
    "CropRegions",
    "DeviceStream",
    "Game",
    "GameTimeoutError",
    "GenericAdbError",
    "MatchMode",
    "NotInitializedError",
    "StreamingNotSupportedError",
    "UnsupportedResolutionError",
]
