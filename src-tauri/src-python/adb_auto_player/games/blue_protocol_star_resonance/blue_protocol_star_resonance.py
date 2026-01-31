from time import sleep

import cv2
import numpy as np
from adb_auto_player.decorators import register_game
from adb_auto_player.game import Game
from adb_auto_player.image_manipulation import Cropping
from adb_auto_player.models.decorators import GameGUIMetadata
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions


@register_game(
    name="Blue Protocol: Star Resonance",
    gui_metadata=GameGUIMetadata(),
)
class BlueProtocolStarResonance(Game):
    TOGGLE_DISPLAY_POINT = Point(60, 990)

    def __init__(self) -> None:
        super().__init__()
        self.supported_resolutions: list[str] = ["1920x1080"]
        self.package_name_prefixes = ["com.bpsr."]

    @property
    def settings(self):
        raise RuntimeError("Not Implemented")

    def close_popups(self) -> None:
        power_savings_templates = self.get_templates_from_dir("power_saving_mode")
        daily_reset = self.get_templates_from_dir("daily_reset")
        while result := self.find_any_template(
            power_savings_templates + daily_reset,
        ):
            self.tap(result)
            sleep(3)

    def hide_ui(self) -> None:
        while not self.is_ui_hidden():
            self.tap(self.TOGGLE_DISPLAY_POINT)
            sleep(1)

    def show_ui(self) -> None:
        while self.is_ui_hidden():
            self.tap(self.TOGGLE_DISPLAY_POINT)
            sleep(1)

    def is_ui_hidden(
        self,
        min_white_portion: float = 0.20,
        min_white_threshold=250,
    ) -> bool:
        """Checks if UI is hidden.

        Specifically checks for the white camera and emote button.
        """
        result = Cropping.crop(
            self.get_screenshot(),
            crop_regions=CropRegions(
                top="73%",
                bottom="14%",
                left="2%",
                right="96%",
            ),
        )

        white_mask = cv2.inRange(
            result.image,
            np.array([min_white_threshold] * 3, dtype=np.uint8),
            np.array([255, 255, 255], dtype=np.uint8),
        )

        white_pixel_count = cv2.countNonZero(white_mask)
        total_pixels = result.image.shape[0] * result.image.shape[1]

        white_fraction = white_pixel_count / total_pixels

        # UI is hidden if NOT enough white is present
        return white_fraction < min_white_portion

    @property
    def character_center(self) -> Point:
        return Point(self.center.x, self.center.y + 80)
