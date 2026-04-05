import logging
from time import sleep

import cv2
import numpy as np
from adb_auto_player.decorators import register_command
from adb_auto_player.image_manipulation import Cropping
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.util import StringHelper, SummaryGenerator

from .blue_protocol_star_resonance import BlueProtocolStarResonance


class WondrousTag(BlueProtocolStarResonance):
    clear_count = 0

    @register_command(
        gui=GUIMetadata(
            label="Wondrous Tag",
        ),
        name="BPSR.tag",
    )
    def entry(self) -> None:
        self.start_stream()
        logging.info("Starting Tag!")
        self.close_popups()
        self.show_ui()
        while True:
            self.close_popups()
            self.tag()
            sleep(1)

    def tag(self) -> None:
        if self.get_wondrous_tag_interact_option():
            sleep(2)  # there's a chance the labels dont load at the same time
            if label := self.get_wondrous_tag_interact_option():
                self.tap(label)
            return

        if match := self.game_find_template_match("wondrous_tag/match"):
            self.tap(match)
            return

        if accept := self.game_find_template_match("wondrous_tag/accept"):
            self.tap(accept)
            return

        if leave := self.game_find_template_match("wondrous_tag/leave"):
            self.tap(leave)
            self.clear_count += 1
            logging.info(f"Wondrous Tag matches: {self.clear_count}")
            SummaryGenerator.increment("Wondrous Tag", "Matches")
            SummaryGenerator.increment(
                "Currency",
                "Starland Medal",
                5,
            )
            sleep(5)
            return

        if self.game_find_template_match("wondrous_tag/cancel"):
            sleep(5)
            return

        if self.i_am_inside_dialogue():
            self.tap(Point(1845, 55))
        return

    def get_wondrous_tag_interact_option(self) -> None | Box:
        exact_keywords = ["Wondrous", "Tag", "Wondrous Tag"]

        for label in self.get_interact_options():
            for keyword in exact_keywords:
                if StringHelper.fuzzy_substring_match(label.text, keyword):
                    return label.box

            if StringHelper.fuzzy_substring_match(label.text, "Meowflyn"):
                return label.box.with_offset(Point(0, 90))

        return None

    def i_am_inside_dialogue(
        self,
        min_white_threshold: int = 220,
        min_white_ratio: float = 0.5,
    ) -> bool:
        # TODO should check top right corner too
        result = Cropping.crop_to_box(
            self.get_screenshot(),
            Box(
                top_left=Point(58, 40),
                width=26,
                height=26,
            ),
        )

        gray = cv2.cvtColor(result.image, cv2.COLOR_BGR2GRAY)
        white_pixels = np.sum(gray >= min_white_threshold)
        total_pixels = gray.size

        white_ratio = white_pixels / total_pixels
        return bool(white_ratio > min_white_ratio)
