import logging
from time import sleep
from typing import NoReturn

from adb_auto_player import Coordinates, Game
from adb_auto_player.decorators.register_command import GuiMetadata, register_command
from adb_auto_player.decorators.register_game import register_game
from pydantic import BaseModel


@register_game(
    name="Guitar Girl",
)
class GuitarGirl(Game):
    def __init__(self) -> None:
        """Initialize AFKJourneyBase."""
        super().__init__()
        self.supports_portrait = True
        self.package_name = "com.neowiz.game.guitargirl"

    def get_config(self) -> BaseModel:
        raise NotImplementedError()

    def _load_config(self):
        raise NotImplementedError()

    @register_command(gui=GuiMetadata(label="Play"))
    def play(self) -> NoReturn:
        self.open_eyes(device_streaming=False)
        counter = 0
        y = 200
        y_max = 960
        logging.info("Tapping.")
        mod = 10000
        while True:
            if counter == (mod - 1):
                self._start_game_if_not_running()

            if counter == 0:
                logging.info("Leveling up and activating Skills.")
                self._level_up()
                self._activate_skills()

            self.tap(Coordinates(500, y), log=False)
            y += 40
            if y > y_max:
                y = 200

            counter += 1
            counter = counter % mod

    def _level_up(self) -> None:
        for _ in range(10):
            self.tap(Coordinates(900, 1450), log=False)
        self.tap(Coordinates(100, 1450), log=False)
        pass

    def _activate_skills(self) -> None:
        self.tap(Coordinates(200, 1280), log=False)
        sleep(1)
        self.tap(Coordinates(430, 1280), log=False)
        sleep(1)
        self.tap(Coordinates(660, 1280), log=False)

    def _start_game_if_not_running(self) -> None:
        if not self.is_game_running():
            logging.warning("Restarting Guitar Girl.")
            self.start_game()
            sleep(15)
