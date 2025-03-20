"""Avatar: Realms Collide Base Module."""

import logging
from abc import ABC
from pathlib import Path

from adb_auto_player import ConfigLoader, Game, NotInitializedError
from adb_auto_player.games.avatar_realms_collide.config import Config


class AvatarRealmsCollideBase(Game, ABC):
    """Avatar Realms Collide Base Class."""

    def __init__(self) -> None:
        """Initialize AvatarRealmsCollideBase."""
        super().__init__()
        self.package_names = [
            "com.angames.android.google.avatarbendingtheworld",
        ]

    template_dir_path: Path | None = None
    config_file_path: Path | None = None

    def start_up(self, device_streaming: bool = False) -> None:
        """Give the bot eyes."""
        if self.device is None:
            logging.debug("start_up")
            self.open_eyes(device_streaming=device_streaming)
        if self.config is None:
            self.load_config()
            pass

    def get_template_dir_path(self) -> Path:
        """Retrieve path to images."""
        if self.template_dir_path is not None:
            return self.template_dir_path

        self.template_dir_path = (
            ConfigLoader().games_dir / "avatar_realms_collide" / "templates"
        )
        logging.debug(f"Avatar Realms Collide template path: {self.template_dir_path}")
        return self.template_dir_path

    def load_config(self) -> None:
        """Load config TOML."""
        pass

    def get_config(self) -> Config:
        """Get config."""
        if self.config is None:
            raise NotInitializedError()

        return self.config

    def get_supported_resolutions(self) -> list[str]:
        """Get supported resolutions."""
        return ["1080x1920"]
