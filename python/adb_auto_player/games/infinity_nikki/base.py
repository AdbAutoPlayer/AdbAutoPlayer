import logging
from abc import ABC

from adb_auto_player.config_loader import get_games_dir
from adb_auto_player.exceptions import NotInitializedError
from adb_auto_player.game import Game
from pathlib import Path

from adb_auto_player.games.infinity_nikki.config import Config


class InfinityNikkiBase(Game, ABC):
    def __init__(self) -> None:
        super().__init__()
        self.supports_portrait = False
        self.package_names = [
            "com.infoldgames.infinitynikkias",
        ]

    template_dir_path: Path | None = None
    config_file_path: Path | None = None

    FAST_TIMEOUT: int = 3

    def start_up(self, device_streaming: bool = False) -> None:
        if self.device is None:
            logging.debug("start_up")
            self.set_device(device_streaming=device_streaming)
        if self.config is None:
            self.load_config()
        return None

    def get_template_dir_path(self) -> Path:
        if self.template_dir_path is not None:
            return self.template_dir_path

        games_dir = get_games_dir()
        self.template_dir_path = games_dir / "infinity_nikki" / "templates"
        logging.debug(f"Infinity Nikki template dir: {self.template_dir_path}")
        return self.template_dir_path

    def load_config(self) -> None:
        if self.config_file_path is None:
            self.config_file_path = (
                get_games_dir() / "infinity_nikki" / "InfinityNikki.toml"
            )
            logging.debug(f"Infinity Nikki config path: {self.config_file_path}")
        self.config = Config.from_toml(self.config_file_path)

    def get_config(self) -> Config:
        if self.config is None:
            raise NotInitializedError()
        return self.config

    def get_supported_resolutions(self) -> list[str]:
        return ["1080x1920"]
