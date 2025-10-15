from time import sleep

from adb_auto_player.decorators import register_game
from adb_auto_player.game import Game
from adb_auto_player.models.decorators import GameGUIMetadata
from pydantic import BaseModel


@register_game(
    name="Blue Protocol: Star Resonance",
    gui_metadata=GameGUIMetadata(),
)
class BlueProtocolStarResonance(Game):
    def __init__(self) -> None:
        super().__init__()
        self.supported_resolutions: list[str] = ["1920x1080"]

    def get_settings(self) -> BaseModel:
        raise RuntimeError("Not Implemented")

    def _load_settings(self):
        pass

    def close_power_savings(self) -> None:
        if result := self.find_any_template(
            self.get_templates_from_dir("power_saving_mode")
        ):
            self.tap(result)
            sleep(1)
