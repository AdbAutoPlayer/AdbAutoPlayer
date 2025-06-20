import logging
from time import sleep
from typing import NoReturn

from adb_auto_player import (
    Coordinates,
    Game,
    TapParams,
    TemplateMatchParams,
)
from adb_auto_player.decorators.register_command import GuiMetadata, register_command
from adb_auto_player.decorators.register_game import register_game
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.util.summary_generator import SummaryGenerator
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

    @register_command(gui=GuiMetadata(label="Busk"))
    def busk(self) -> NoReturn:
        self.open_eyes(device_streaming=False)
        counter = 0
        mod = 3000
        while True:
            if counter == (mod - 1):
                self._start_game_if_not_running()

            if counter == 0:
                sleep(3)
                self._check_for_popups()
                self._level_up_guitar_girl()
                self._level_up_classmate_joy()
                self._activate_skills()
                logging.info("Tapping Music Notes.")

            if result := self.find_any_template(
                templates=[
                    "big_note.png",
                    "big_note2.png",
                    "note.png",
                ],
                threshold=0.7,
                crop_regions=CropRegions(bottom=0.5, right=0.2, top=0.05),
            ):
                note, x, y = result
                self.tap(Coordinates(x, y), log_message=None)
                if "big_note" in note:
                    SummaryGenerator().add_count("Big Note")
                else:
                    SummaryGenerator().add_count("Small Note")

            counter += 1
            counter = counter % mod
        # No Return

    @register_command(gui=GuiMetadata(label="Play"))
    def play(self) -> NoReturn:
        self.open_eyes(device_streaming=True)
        counter = 0
        y = 200
        y_max = 960
        mod = 10000
        while True:
            if counter == (mod - 1):
                self._start_game_if_not_running()

            if counter == 0:
                sleep(3)
                self._check_for_popups()
                self._level_up_guitar_girl()
                self._activate_skills()
                logging.info("Tapping.")

            self.tap(Coordinates(500, y), log_message=None)
            y += 40
            if y > y_max:
                y = 200

            counter += 1
            counter = counter % mod
        # NoReturn

    def _level_up_guitar_girl(self) -> None:
        logging.info("Leveling up Guitar Girl.")
        self._open_guitar_girl_tab()

        guitar_girl_level_up = Coordinates(900, 1450)
        for _ in range(50):
            self.tap(guitar_girl_level_up, log_message=None)
        sleep(3)

        guitar_girl_icon = Coordinates(100, 1450)
        for _ in range(3):
            self.tap(guitar_girl_icon, log_message=None)
        sleep(1)

    def _level_up_classmate_joy(self) -> None:
        logging.info("Leveling up Classmate Joy.")
        self._open_follower_tab()

        classmate_joy_level_up = Coordinates(900, 1250)
        for _ in range(50):
            self.tap(classmate_joy_level_up, log_message=None)
        sleep(3)

        classmate_joy_icon = Coordinates(100, 1250)
        for _ in range(3):
            self.tap(classmate_joy_icon, log_message=None)
        sleep(1)

    def _activate_skills(self) -> None:
        logging.info("Activating Skills.")
        self._open_guitar_girl_tab()

        base_x = 200
        y = 1280
        x_offset = 230
        num_skills = 3

        for i in range(num_skills):
            x = base_x + i * x_offset
            self.tap(Coordinates(x, y), log_message=None)
            sleep(1)

    def _start_game_if_not_running(self) -> None:
        if not self.is_game_running():
            logging.warning("Restarting Guitar Girl.")
            self.start_game()
            sleep(15)

    def _open_guitar_girl_tab(self) -> None:
        self.tap(Coordinates(80, 1850), log_message=None)
        sleep(1)

    def _open_follower_tab(self):
        self.tap(Coordinates(210, 1850), log_message=None)
        sleep(1)

    def _check_for_popups(self) -> None:
        logging.info("Checking for popups.")
        while result := self.find_any_template(
            ["close.png", "ok.png"],
        ):
            template, x, y = result
            self._tap_coordinates_till_template_disappears(
                tap_params=TapParams(Coordinates(x, y)),
                template_match_params=TemplateMatchParams(template=template),
            )
            sleep(5)
