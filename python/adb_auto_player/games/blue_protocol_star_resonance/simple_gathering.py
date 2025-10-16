import logging
from time import sleep

from adb_auto_player.decorators import register_command
from adb_auto_player.exceptions import GameTimeoutError
from adb_auto_player.models.decorators import GUIMetadata

from .blue_protocol_star_resonance import BlueProtocolStarResonance


class SimpleGathering(BlueProtocolStarResonance):
    gather_count = 0

    @register_command(
        gui=GUIMetadata(
            label="Simple Gathering",
        ),
        name="BPSR.simple_gathering",
    )
    def entry(self) -> None:
        self.start_stream()
        while True:
            self.close_power_savings()
            self.try_to_gather()
            sleep(1)

    def try_to_gather(self) -> bool:
        self.show_ui()
        if result := self.find_any_template(self.get_templates_from_dir("gathering")):
            self.tap(result)
            try:
                self.wait_until_template_disappears(
                    result.template,
                    delay=0.1,
                    timeout=3,
                )
                template = result.template
                if not template.endswith("_active.png"):
                    template = template.replace(".png", "_active.png")
                self.wait_until_template_disappears(
                    template,
                    delay=0.1,
                    timeout=5,
                )
            except GameTimeoutError:
                return True
            self.gather_count += 1
            logging.info(f"Gathered from Spot #{self.gather_count}")
            sleep(0.5)
            return True
        return False
