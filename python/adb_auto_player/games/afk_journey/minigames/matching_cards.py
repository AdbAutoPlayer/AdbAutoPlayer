import logging
import time
from time import sleep

from adb_auto_player.decorators import register_command
from adb_auto_player.image_manipulation import Cropping, Scaling
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.template_matching import TemplateMatcher

from ..base import AFKJourneyBase
from ..gui_category import AFKJCategory

MATCH_TARGET_BOX = Box(
    top_left=Point(80, 160),
    width=80,
    height=100,
)

MATCH_AREA_BOX = Box(
    top_left=Point(150, 440),
    width=770,
    height=1180,
)

MATCH_TARGET_SCALE = 1.8  # 180%


class MatchingCards(AFKJourneyBase):
    @register_command(
        gui=GUIMetadata(
            label="Matching Cards",
            category=AFKJCategory.EVENTS_AND_OTHER,
        ),
    )
    def matching_cards(self) -> None:
        """Matching Card minigame.

        This assumes you are already in the game.

        Raises:
            GameTimeoutError: If game timed out.
        """
        self.start_up(device_streaming=True)

        self.assert_no_scaling(
            "Matching Cards is optimized for 1080x1920 it will not work with other "
            "resolutions."
        )
        self.assert_frame_and_input_delay_below_threshold()

        self.wait_for_any_template(
            [
                "minigames/matching_cards/x.png",
                "minigames/matching_cards/pause.png",
            ],
            crop_regions=CropRegions(
                left="85%",
                top="5%",
                bottom="85%",
            ),
            timeout=5,
            timeout_message="Not in game window",
            threshold=ConfidenceValue("95%"),
        )
        crop_result = Cropping.crop_to_box(self.get_screenshot(), MATCH_TARGET_BOX)
        target = Scaling.scale_percent(crop_result.image, MATCH_TARGET_SCALE)
        logging.info("Starting Matching Cards ...")
        self.tap(
            Point(int(1080 / 2), int(1920 / 2)),
            log=False,
        )
        sleep(3)

        start_time = time.time()
        last_match_time = start_time

        five_seconds = 5
        sixty_seconds = 60
        while time.time() - start_time < sixty_seconds:
            cropped = Cropping.crop_to_box(
                self.get_screenshot(),
                MATCH_AREA_BOX,
            )
            if result := TemplateMatcher.find_template_match(
                cropped.image,
                target,
                threshold=ConfidenceValue("60%"),
            ):
                self.tap(result.with_offset(cropped.offset), log=False)
                last_match_time = time.time()

            if time.time() - last_match_time > five_seconds:
                # game is finished
                break

            sleep(1.0 / 30.0)
        logging.info("Matching Cards done")
