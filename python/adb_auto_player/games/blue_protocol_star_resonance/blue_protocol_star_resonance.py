from time import sleep

import cv2
import numpy as np
from adb_auto_player.decorators import register_game
from adb_auto_player.game import Game
from adb_auto_player.image_manipulation import Cropping
from adb_auto_player.models.decorators import GameGUIMetadata
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions
from pydantic import BaseModel


@register_game(
    name="Blue Protocol: Star Resonance",
    gui_metadata=GameGUIMetadata(),
)
class BlueProtocolStarResonance(Game):
    TOGGLE_DISPLAY_POINT = Point(60, 990)

    def __init__(self) -> None:
        super().__init__()
        self.supported_resolutions: list[str] = ["1920x1080"]

    def get_settings(self) -> BaseModel:
        raise RuntimeError("Not Implemented")

    def close_power_savings(self) -> None:
        if result := self.find_any_template(
            self.get_templates_from_dir("power_saving_mode")
        ):
            self.tap(result)
            sleep(1)

    def hide_ui(self) -> None:
        while not self.is_ui_hidden():
            self.tap(self.TOGGLE_DISPLAY_POINT)
            sleep(1)

    def show_ui(self) -> None:
        while self.is_ui_hidden():
            self.tap(self.TOGGLE_DISPLAY_POINT)
            sleep(1)

    def is_ui_hidden(self, max_proportion: float = 0.05) -> bool:
        """Checks if UI is hidden by looking for the health bar."""
        result = Cropping.crop(
            self.get_screenshot(),
            crop_regions=CropRegions(
                top="93%",
                bottom="5%",
                left="40%",
                right="35%",
            ),
        )

        min_color = np.array([161, 204, 63], dtype=np.uint8)
        max_color = np.array([210, 254, 110], dtype=np.uint8)

        # Create mask of pixels in the range
        mask = cv2.inRange(result.image, min_color, max_color)

        # Count non-zero pixels in the mask
        count = cv2.countNonZero(mask)

        # Proportion of matching pixels
        proportion = count / (result.image.shape[0] * result.image.shape[1])
        return proportion <= max_proportion

    @property
    def character_center(self) -> Point:
        return Point(self.center.x, self.center.y + 80)
