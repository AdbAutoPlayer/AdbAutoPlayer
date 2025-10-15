from time import sleep

from adb_auto_player.decorators import register_command
from adb_auto_player.models.decorators import GUIMetadata

from .blue_protocol_star_resonance import BlueProtocolStarResonance


class SimpleGathering(BlueProtocolStarResonance):
    @register_command(
        gui=GUIMetadata(
            label="Simple Gathering",
        ),
        name="BPSR.simple_gathering",
    )
    def entry(self) -> None:
        while True:
            self.close_power_savings()
            self.gather()
            sleep(1)

    def gather(self) -> None:
        if result := self.find_any_template(self.get_templates_from_dir("gathering")):
            self.tap(result)
