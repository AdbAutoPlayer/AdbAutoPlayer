"""ADB Auto Player Game Base Module."""

import logging
from abc import abstractmethod
from functools import cached_property
from pathlib import Path

from adb_auto_player.device.adb import AdbController, DeviceStream
from adb_auto_player.exceptions import AutoPlayerUnrecoverableError
from adb_auto_player.file_loader import SettingsLoader
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.device import DisplayInfo, Resolution
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.pydantic.app_settings import AppSettings
from adb_auto_player.registries import GAME_REGISTRY
from pydantic import BaseModel

from ._base import _GameBase
from ._input_mixin import _InputMixin
from ._lifecycle_mixin import _LifecycleMixin
from ._screenshot_mixin import _ScreenshotMixin
from ._task_mixin import _TaskMixin
from ._template_mixin import _TemplateMixin


class Game(
    _InputMixin,
    _ScreenshotMixin,
    _TemplateMixin,
    _LifecycleMixin,
    _TaskMixin,
    _GameBase,
):
    """Generic Game base class.

    Composes input, screenshot, template-matching, lifecycle and task-execution
    capabilities. Concrete game classes must implement the *settings* abstract
    property.
    """

    def __init__(self) -> None:
        """Initialize shared game state."""
        self.default_threshold: ConfidenceValue = ConfidenceValue("90%")

        # e.g. AFK Journey
        #   Global: com.farlightgames.igame.gp
        #   Vietnam: com.farlightgames.igame.gp.vn
        #   Global will cover both cases because it checks for the prefix
        self.package_name_prefixes: list[str] = []
        # Assuming landscape for most games
        self.base_resolution: Resolution = Resolution.from_string("1920x1080")
        self._device: AdbController | None = None
        self._stream: DeviceStream | None = None
        self._target_package_name: str | None = None

    # ------------------------------------------------------------------
    # Abstract interface (concrete games must implement)
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def settings(self) -> BaseModel:
        """Game-specific settings."""
        ...

    # ------------------------------------------------------------------
    # Concrete properties
    # ------------------------------------------------------------------

    @cached_property
    def app_settings(self) -> AppSettings:
        """Global application settings (loaded from App.toml)."""
        try:
            app_config_dir = SettingsLoader.get_app_config_dir().parent
            app_settings_path = app_config_dir / "App.toml"
            return AppSettings.from_toml(app_settings_path)
        except Exception:
            return AppSettings()

    @property
    def template_timeout(self) -> float:
        """Global template-wait timeout from app settings."""
        return self.app_settings.advanced.template_timeout

    @property
    def device(self) -> AdbController:
        """Lazily-initialised ADB device controller."""
        if self._device is None:
            self._device = AdbController()
        return self._device

    @property
    def display_info(self) -> DisplayInfo:
        """Current device display information."""
        return self.device.get_display_info()

    @property
    def center(self) -> Point:
        """Center point of the base resolution."""
        return self.base_resolution.center

    @property
    def settings_file_path(self) -> Path:
        """Path to the game's TOML settings file."""
        settings_file: str | None = None
        for module, game in GAME_REGISTRY.items():
            if module == self._get_game_module():
                settings_file = game.settings_file
                break

        if settings_file is None:
            raise AutoPlayerUnrecoverableError("Game does not have any Settings")
        return SettingsLoader.settings_dir() / settings_file

    @cached_property
    def template_dir(self) -> Path:
        """Directory containing the game's template images."""
        module = self._get_game_module()
        template_dir = SettingsLoader.games_dir() / module / "templates"
        logging.debug(f"{module} template path: {template_dir}")
        return template_dir
