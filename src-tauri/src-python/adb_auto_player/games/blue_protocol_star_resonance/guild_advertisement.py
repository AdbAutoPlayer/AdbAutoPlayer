import logging
import random
import re
from time import sleep

from adb_auto_player.decorators import register_command
from adb_auto_player.image_manipulation import Cropping
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.ocr import PSM, TesseractBackend, TesseractConfig

from .blue_protocol_star_resonance import BlueProtocolStarResonance


class GuildAdvertisement(BlueProtocolStarResonance):
    AD_INDEX: int = 0

    @staticmethod
    def get_ads() -> list[str]:
        return [
            "Tired of pugging Raids and M5? Join BreadFisch 3|4|8|1|8|5|0 experienced "
            "or new and willing to learn just apply!",
            "BreadFisch 3|4|8|1|8|5|0 New guild of experienced players looking for "
            "recruits, all welcome so long as you're active and friendly",
            "BreadFisch 3|4|8|1|8|5|0 • New Guild Veteran Players • EN • Willing To "
            "Teach & Help You Grow",
        ]

    @register_command(
        gui=GUIMetadata(
            label="Guild Advertisement",
        ),
        name="BPSR.guild_advertisement",
    )
    def entry(self) -> None:
        self.start_stream()
        logging.info("Posting Guild Advertisement in World Chat!")
        self.close_popups()
        if not self.is_chat_open():
            self.show_ui()

        self.AD_INDEX = random.randrange(len(self.get_ads()))

        while True:
            self.close_popups()
            self.open_world_chat()
            self.advertise_in_world_chat()
            sleep(300)

    def advertise_in_world_chat(self) -> None:
        for i in range(1, 26):
            if not self.is_in_world_chat_channel(i):
                self.switch_world_chat_channel(i)
            if self.is_in_world_chat_channel(i):
                self.post_ad_in_chat()
        self.AD_INDEX = (self.AD_INDEX + 1) % len(self.get_ads())

    def is_in_world_chat_channel(self, channel: int) -> bool:
        result = Cropping.crop_to_box(
            self.get_screenshot(),
            box=Box(
                top_left=Point(380, 40),
                width=70,
                height=40,
            ),
        )

        ocr = TesseractBackend(config=TesseractConfig(psm=PSM.SINGLE_LINE))
        text = ocr.extract_text(result.image)

        digits = re.sub(r"\D", "", text)

        if not digits:
            return False

        try:
            return int(digits) == channel
        except ValueError:
            return False

    def switch_world_chat_channel(self, channel: int) -> None:
        # Open World Chat Channel Selector
        self.tap(Point(300, 60))
        sleep(2)

        for digit_char in str(channel):
            digit = int(digit_char)
            point = self.get_channel_select_buttons()[digit]
            self.tap(point)
            sleep(1)

        self.tap(self.get_channel_select_buttons()["OK"])
        sleep(3)

    def post_ad_in_chat(self):
        # Please enter text...
        self.tap(Point(268, 1020))
        sleep(3)
        self.device.d.d.send_keys(self.get_ads()[self.AD_INDEX])
        sleep(3)
        # OK
        self.tap(Point(1840, 1020))
        send = self.wait_for_template(
            "guild_advertisement/send.png",
            crop_regions=CropRegions(
                left="50%",
                right="30%",
                top="90%",
            ),
        )
        self.tap(send)
        sleep(3)

    def is_chat_open(self) -> bool:
        return (
            self.game_find_template_match(
                "guild_advertisement/chat_active.png",
                crop_regions=CropRegions(
                    right="90%",
                    top="10%",
                    bottom="80%",
                ),
            )
            is not None
        )

    def open_world_chat(self) -> None:
        if not self.is_chat_open():
            # Open Chat Window
            self.tap(Point(730, 900))
            sleep(5)

        # Enter World Chat
        self.tap(Point(160, 170))
        sleep(5)

    @staticmethod
    def get_channel_select_buttons() -> dict[str | int, Point]:
        return {
            1: Point(280, 140),
            2: Point(370, 140),
            3: Point(460, 140),
            4: Point(280, 230),
            5: Point(370, 230),
            6: Point(460, 230),
            7: Point(280, 320),
            8: Point(370, 320),
            9: Point(460, 320),
            0: Point(540, 230),
            "OK": Point(540, 320),
        }
