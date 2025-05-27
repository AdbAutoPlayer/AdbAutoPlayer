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
        mod = 10000
        while True:
            if counter == (mod - 1):
                self._start_game_if_not_running()

            if counter == 0:
                logging.info("Leveling up and activating Skills.")
                sleep(3)  # wait for queued taps to complete
                self._level_up()
                self._activate_skills()
                logging.info("Tapping.")

            self.tap(Coordinates(500, y), log=False)
            y += 40
            if y > y_max:
                y = 200

            counter += 1
            counter = counter % mod

    def _level_up(self) -> None:
        self._open_guitar_girl_tab()

        guitar_girl_level_up = Coordinates(900, 1450)
        for _ in range(10):
            self.tap(guitar_girl_level_up, log=False)

        sleep(1)
        guitar_girl_icon = Coordinates(100, 1450)
        for _ in range(3):
            self.tap(guitar_girl_icon, log=False)

    def _activate_skills(self) -> None:
        self._open_guitar_girl_tab()

        base_x = 200
        y = 1280
        x_offset = 230
        num_skills = 3

        for i in range(num_skills):
            x = base_x + i * x_offset
            self.tap(Coordinates(x, y), log=False)
            sleep(1)

    def _start_game_if_not_running(self) -> None:
        if not self.is_game_running():
            logging.warning("Restarting Guitar Girl.")
            self.start_game()
            sleep(15)

    def _open_guitar_girl_tab(self) -> None:
        sleep(1)
        self.tap(Coordinates(80, 1850), log=False)
        sleep(1)
