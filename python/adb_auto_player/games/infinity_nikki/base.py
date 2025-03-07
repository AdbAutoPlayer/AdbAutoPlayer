"""Infinity Nikki Base Module."""

import logging
from abc import ABC
from pathlib import Path

from adb_auto_player import ConfigLoader, Game, NotInitializedError
from adb_auto_player.games.infinity_nikki import Config


class InfinityNikkiBase(Game, ABC):
    """Infinity Nikki Base Class."""

    def __init__(self) -> None:
        """Initialize InfinityNikkiBase."""
        super().__init__()
        self.package_names = [
            "com.infoldgames.infinitynikki",
        ]

    template_dir_path: Path | None = None
    config_file_path: Path | None = None

    FAST_TIMEOUT: int = 3

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

        games_dir = ConfigLoader().games_dir
        self.template_dir_path = games_dir / "infinity_nikki" / "templates"
        logging.debug(f"Infinity Nikki template dir: {self.template_dir_path}")
        return self.template_dir_path

    def load_config(self) -> None:
        """Load config TOML."""
        if self.config_file_path is None:
            self.config_file_path = (
                ConfigLoader().games_dir / "infinity_nikki" / "InfinityNikki.toml"
            )
            logging.debug(f"Infinity Nikki config path: {self.config_file_path}")
        self.config = Config.from_toml(self.config_file_path)

    def get_config(self) -> Config:
        """Get config."""
        if self.config is None:
            raise NotInitializedError()
        return self.config

    def get_supported_resolutions(self) -> list[str]:
        """Get supported resolutions."""
        return ["1080x1920"]
