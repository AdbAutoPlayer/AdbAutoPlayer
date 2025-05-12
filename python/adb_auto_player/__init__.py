"""ADB Auto Player Package."""

from adb_auto_player.config.game_config_base import ConfigBase

from .command import Command
from .config_loader import ConfigLoader
from .device_stream import DeviceStream, StreamingNotSupportedError
from .exceptions import (
    GameTimeoutError,
    GenericAdbError,
    NoPreviousScreenshotError,
    NotFoundError,
    NotInitializedError,
    UnsupportedResolutionError,
)
from .game import Coordinates, Game
from .template_matching import CropRegions, MatchMode

__all__: list[str] = [
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
    "NoPreviousScreenshotError",
    "NotFoundError",
    "NotInitializedError",
    "StreamingNotSupportedError",
    "UnsupportedResolutionError",
]
