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
from .game import Coordinates, Game, TapParams, TemplateMatchParams
from .template_matching import CropRegions, MatchMode

__all__: list[str] = [
    "AutoPlayerError",
    "AutoPlayerUnrecoverableError",
    "AutoPlayerWarningError",
    "Command",
    "ConfigBase",
    "ConfigLoader",
    "Coordinates",
    "CropRegions",
    "DeviceStream",
    "Game",
    "GameActionFailedError",
    "GameNotRunningOrFrozenError",
    "GameStartError",
    "GameTimeoutError",
    "GenericAdbError",
    "GenericAdbUnrecoverableError",
    "MatchMode",
    "NotInitializedError",
    "StreamingNotSupportedError",
    "TapParams",
    "TemplateMatchParams",
    "UnsupportedResolutionError",
]
