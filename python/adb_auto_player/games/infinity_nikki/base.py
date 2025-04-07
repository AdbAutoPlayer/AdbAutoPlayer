"""Infinity Nikki Base Module."""

import logging
from abc import ABC

from adb_auto_player import Game, NotInitializedError
from adb_auto_player.games.infinity_nikki import Config


class InfinityNikkiBase(Game, ABC):
    """Infinity Nikki Base Class."""

    def __init__(self) -> None:
        """Initialize InfinityNikkiBase."""
        super().__init__()
        self.package_names = [
            "com.infoldgames.infinitynikki",
        ]

    FAST_TIMEOUT: int = 3

    def start_up(self, device_streaming: bool = False) -> None:
        """Give the bot eyes."""
        if self.device is None:
            logging.debug("start_up")
            self.open_eyes(device_streaming=device_streaming)
        if self.config is None:
            self.load_config()
        logging.warning(
            "This game does not automatically scale on resolution change: "
            "https://AdbAutoPlayer.github.io/AdbAutoPlayer/user-guide/troubleshoot.html"
            "#tap-to-restart-this-app-for-a-better-view"
        )

    def load_config(self) -> None:
        """Load config TOML."""
        self.config = Config.from_toml(self._get_config_file_path())

    def get_config(self) -> Config:
        """Get config."""
        if self.config is None:
            raise NotInitializedError()
        return self.config
