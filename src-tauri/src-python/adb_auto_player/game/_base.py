"""Game abstract base — declares the complete interface shared by all Game mixins."""

from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from time import sleep
from typing import Literal

import numpy as np
from adb_auto_player.device.adb import AdbController, DeviceStream
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.device import DisplayInfo, Resolution
from adb_auto_player.models.geometry import Coordinates, Point
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.models.pydantic.app_settings import AppSettings
from adb_auto_player.models.template_matching import MatchMode, TemplateMatchResult
from pydantic import BaseModel


class _GameBase(ABC):
    """Full abstract interface that all Game mixins share.

    Declares every attribute and method used across mixin boundaries so that
    individual mixins can reference *self.xxx* and still satisfy the type checker.
    Each mixin implements its own slice; *Game* wires them together.
    """

    # ------------------------------------------------------------------
    # Instance attributes — set by Game.__init__
    # ------------------------------------------------------------------
    default_threshold: ConfidenceValue
    package_name_prefixes: list[str]
    base_resolution: Resolution
    _device: AdbController | None
    _stream: DeviceStream | None
    _target_package_name: str | None

    # ------------------------------------------------------------------
    # Properties — implemented by Game
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def settings(self) -> BaseModel:
        """Game-specific settings (implemented by each concrete game class)."""
        ...

    @property
    @abstractmethod
    def device(self) -> AdbController:
        """Active ADB device controller."""
        ...

    @property
    @abstractmethod
    def display_info(self) -> DisplayInfo:
        """Current device display information."""
        ...

    @property
    @abstractmethod
    def center(self) -> Point:
        """Center point of the base resolution."""
        ...

    @property
    @abstractmethod
    def template_timeout(self) -> float:
        """Global template-wait timeout from app settings."""
        ...

    @property
    @abstractmethod
    def settings_file_path(self) -> Path:
        """Path to the game's TOML settings file."""
        ...

    @cached_property
    @abstractmethod
    def app_settings(self) -> AppSettings:
        """Global application settings."""
        ...

    @cached_property
    @abstractmethod
    def template_dir(self) -> Path:
        """Directory containing the game's template images."""
        ...

    # ------------------------------------------------------------------
    # Cross-mixin method stubs — implemented by their respective mixins
    # ------------------------------------------------------------------
    # Declared here so that sibling mixins can call self.xxx without type errors.

    # _InputMixin
    @abstractmethod
    def tap(
        self,
        coordinates: Coordinates,
        scale: bool = False,
        blocking: bool = True,
        non_blocking_sleep_duration: float | None = 1 / 30,
        log_message: str | None = None,
        log: bool = True,
    ) -> None: ...

    @abstractmethod
    def press_back_button(self) -> None: ...

    # _ScreenshotMixin
    @abstractmethod
    def get_screenshot(self) -> np.ndarray: ...

    @abstractmethod
    def start_stream(self) -> None: ...

    @abstractmethod
    def stop_stream(self) -> None: ...

    @abstractmethod
    def _set_device_resolution(self) -> None: ...

    @abstractmethod
    def _check_requirements(self) -> None: ...

    @abstractmethod
    def _start_device_streaming(self, device_streaming: bool = True) -> None: ...

    @abstractmethod
    def _check_screenshot_matches_display_resolution(
        self, device_streaming_check: bool = False
    ) -> None: ...

    # _TemplateMixin
    @abstractmethod
    def game_find_template_match(
        self,
        template: str | Path,
        match_mode: MatchMode = MatchMode.BEST,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        screenshot: np.ndarray | None = None,
    ) -> TemplateMatchResult | None: ...

    @abstractmethod
    def find_any_template(
        self,
        templates: list[str],
        match_mode: MatchMode = MatchMode.BEST,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        screenshot: np.ndarray | None = None,
    ) -> TemplateMatchResult | None: ...

    @abstractmethod
    def wait_for_template(
        self,
        template: str | Path,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        delay: float = 0.5,
        timeout: float | None = None,
        timeout_message: str | None = None,
    ) -> TemplateMatchResult: ...

    @abstractmethod
    def wait_for_any_template(
        self,
        templates: list[str],
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        delay: float = 0.5,
        timeout: float | None = None,
        timeout_message: str | None = None,
        ensure_order: bool = True,
    ) -> TemplateMatchResult: ...

    @abstractmethod
    def wait_for_roi_change(
        self,
        start_image: np.ndarray,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        delay: float = 0.5,
        timeout: float = 30,
        timeout_message: str | None = None,
    ) -> Literal[True]: ...

    @abstractmethod
    def _tap_till_template_disappears(
        self,
        template: str,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        tap_delay: float = 10.0,
        sleep_duration: float = 0.5,
        error_message: str | None = None,
    ) -> None: ...

    @abstractmethod
    def _tap_coordinates_till_template_disappears(
        self,
        coordinates: Coordinates,
        template: str,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions | None = None,
        scale: bool = False,
        delay: float = 10.0,
        max_tap_count: int = 3,
    ) -> None: ...

    # _LifecycleMixin
    @abstractmethod
    def force_stop_game(self) -> None: ...

    @abstractmethod
    def is_game_running(self) -> bool: ...

    @abstractmethod
    def start_game(self) -> None: ...

    @abstractmethod
    def restart_game(self) -> None: ...

    # ------------------------------------------------------------------
    # Concrete utility methods (depend only on app_settings)
    # ------------------------------------------------------------------

    def sleep_action(self) -> None:
        """Sleep for the standard action delay."""
        sleep(self.app_settings.advanced.action_delay)

    def sleep_navigation(self) -> None:
        """Sleep for the navigation-transition delay."""
        sleep(self.app_settings.advanced.navigation_delay)

    def _get_game_module(self) -> str:
        """Return the game's module name (segment after 'games' in module path)."""
        parts = self.__class__.__module__.split(".")
        try:
            index = parts.index("games")
            return parts[index + 1]
        except ValueError:
            raise ValueError("'games' not found in module path")
        except IndexError:
            raise ValueError("No module found after 'games' in module path")
