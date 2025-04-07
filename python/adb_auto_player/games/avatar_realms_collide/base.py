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

    def start_up(self, device_streaming: bool = False) -> None:
        """Give the bot eyes."""
        if self.device is None:
            logging.debug("start_up")
            self.open_eyes(device_streaming=device_streaming)
        if self.config is None:
            self.load_config()

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
        if self.config_file_path is None:
            self.config_file_path = (
                ConfigLoader().games_dir
                / "avatar_realms_collide"
                / "AvatarRealmsCollide.toml"
            )
            logging.debug(f"Avatar Realms Collide config path: {self.config_file_path}")
        self.config = Config.from_toml(self.config_file_path)

    def get_config(self) -> Config:
        """Get config."""
        if self.config is None:
            raise NotInitializedError()

        return self.config
