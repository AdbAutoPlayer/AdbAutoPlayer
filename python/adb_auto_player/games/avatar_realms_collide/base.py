"""Avatar: Realms Collide Base Module."""

import logging
from abc import ABC

from adb_auto_player import Game
from adb_auto_player.games.avatar_realms_collide.config import Config


class AvatarRealmsCollideBase(Game, ABC):
    """Avatar Realms Collide Base Class."""

    def __init__(self) -> None:
        """Initialize AvatarRealmsCollideBase."""
        super().__init__()
        self.package_name_substrings = [
            "com.angames.android.google.avatarbendingtheworld",
        ]

    def start_up(self, device_streaming: bool = False) -> None:
        """Give the bot eyes."""
        if self.device is None:
            logging.debug("start_up")
            self.open_eyes(device_streaming=device_streaming)

    def _load_config(self) -> Config:
        """Load config TOML."""
        self.config = Config.from_toml(self._get_config_file_path())
        return self.config

    def get_config(self) -> Config:
        """Get config."""
        if self.config is None:
            return self._load_config()

        return self.config
