import logging
from datetime import datetime
from time import sleep

import cv2
import numpy as np
from adb_auto_player.decorators import register_command
from adb_auto_player.device.adb import ATTranslatedSet2Keyboard
from adb_auto_player.exceptions import AutoPlayerError, AutoPlayerUnrecoverableError
from adb_auto_player.image_manipulation import Cropping
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.ocr import PSM, TesseractBackend, TesseractConfig
from adb_auto_player.util import StringHelper, SummaryGenerator

from .blue_protocol_star_resonance import BlueProtocolStarResonance


class Devourer(BlueProtocolStarResonance):
    CUMULATIVE_DROP_LIMIT_NORMAL_AND_HARD_MODE: int = 800
    CUMULATIVE_DROP_LIMIT_MASTER_1_TO_5: int = 800

    W = ATTranslatedSet2Keyboard.get_input_event_codes()["W"]
    LIFE_BLOOM = ATTranslatedSet2Keyboard.get_input_event_codes()["1"]
    NOURISH = ATTranslatedSet2Keyboard.get_input_event_codes()["2"]
    BLOSSOM_CHARGE = ATTranslatedSet2Keyboard.get_input_event_codes()["3"]

    keyboard: ATTranslatedSet2Keyboard
    clear_count: int = 0

    @register_command(
        gui=GUIMetadata(
            label="Devourer Normal",
        ),
        name="BPSR.devourer",
    )
    def entry(self) -> None:
        self.start_stream()
        try:
            self.keyboard = ATTranslatedSet2Keyboard()
            self.keyboard.ev_syn()
            logging.info("Using AT Translated Set 2 Keyboard")
        except AutoPlayerError:
            raise AutoPlayerUnrecoverableError(
                "Cannot initialize Xiaomi Joystick or AT Translated Set 2 Keyboard"
                " for steering"
            )

        logging.info("Starting Devourer Normal!")
        logging.info("Current Time: %s", datetime.now())
        self.close_popups()
        self.show_ui()

        if not self.get_devourer_interact_option():
            logging.error("Cannot find Devourer Cage enter button")
            return

        while True:
            self.close_popups()
            self.devourer()
            sleep(1)

    def devourer(self) -> None:
        if label := self.get_devourer_interact_option():
            self.tap(label)
            sleep(5)
        else:
            sleep(5)
            return

        challenge = self.wait_for_template("dungeon/challenge")
        self.click_solo_duo_checkbox()
        self.tap(challenge)
        sleep(15)

        self.wait_for_template("dungeon/exit", timeout=60)
        sleep(3)
        investigate = self.get_dungeon_start_interact_option()
        while investigate is None:
            self.keyboard.hold(self.W)
            sleep(1)
            self.keyboard.release(self.W)
            sleep(0.1)
            investigate = self.get_dungeon_start_interact_option()

        self.tap(investigate)
        challenge = self.wait_for_template("dungeon/challenge")
        self.tap(challenge)
        sleep(15)
        self.handle_battle()
        return

    def heal(self) -> None:
        for _ in range(3):
            self.keyboard.press(self.BLOSSOM_CHARGE)
            sleep(0.1)
            self.keyboard.press(self.NOURISH)
            sleep(0.1)
            self.keyboard.press(self.LIFE_BLOOM)
            sleep(0.1)

    def inside_boss_stage(self) -> bool:
        crop_result = Cropping.crop_to_box(
            self.get_screenshot(),
            Box(
                top_left=Point(120, 330),
                width=300,
                height=70,
            ),
        )

        ocr = TesseractBackend(config=TesseractConfig(psm=PSM.DEFAULT))
        ocr_results = ocr.detect_text_lines(
            crop_result.image,
            min_confidence=ConfidenceValue("80%"),
        )
        expected_lines = ["(0/1) Defeat The Light", "Devourer"]
        for result in ocr_results:
            for line in expected_lines:
                if StringHelper.fuzzy_substring_match(result.text, line):
                    return True
        return False

    def get_dungeon_start_interact_option(self) -> None | Box:
        exact_keywords = ["Investigate"]
        for label in self.get_interact_options(expected_number_of_options=1):
            for keyword in exact_keywords:
                if StringHelper.fuzzy_substring_match(label.text, keyword):
                    return label.box

        return None

    def get_devourer_interact_option(self) -> None | Box:
        exact_keywords = ["Devourer", "Cage", "Devourer Cage"]

        for label in self.get_interact_options(expected_number_of_options=1):
            for keyword in exact_keywords:
                if StringHelper.fuzzy_substring_match(label.text, keyword):
                    return label.box

        return None

    def click_solo_duo_checkbox(
        self,
        min_white_threshold: int = 220,
        min_white_ratio: float = 0.8,
    ):
        result = Cropping.crop_to_box(
            self.get_screenshot(),
            Box(
                top_left=Point(1365, 880),
                width=15,
                height=15,
            ),
        )

        gray = cv2.cvtColor(result.image, cv2.COLOR_BGR2GRAY)
        white_pixels = np.sum(gray >= min_white_threshold)
        total_pixels = gray.size

        white_ratio = white_pixels / total_pixels

        if white_ratio > min_white_ratio:
            self.tap(Point(1365, 880))
            sleep(1)

    def handle_battle(self):
        while True:
            if self.inside_boss_stage():
                self.attack_boss()
                continue

            if next_btn := self.game_find_template_match("dungeon/next"):
                sleep(0.5)
                self.tap(next_btn)
                sleep(2)

            if leave := self.game_find_template_match("dungeon/leave"):
                sleep(0.5)
                self.tap(leave)

                self.clear_count += 1
                logging.info(f"Devourer Cage cleared: {self.clear_count}")
                SummaryGenerator.increment("Devourer Cage", "Cleared")
                SummaryGenerator.increment(
                    "Items",
                    "Dreamweave Dust",
                    3,
                )
                return

            self.heal()
            sleep(3)

    def attack_boss(self):
        normal_attack = Point(1680, 830)
        for _ in range(10):
            self.tap(normal_attack, log=False)
            sleep(0.25)
