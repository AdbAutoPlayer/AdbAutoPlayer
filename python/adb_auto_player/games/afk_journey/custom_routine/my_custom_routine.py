import logging

from adb_auto_player.decorators import register_command
from adb_auto_player.models.decorators import GUIMetadata

from ..base import AFKJourneyBase


class AFKJCustomRoutine(AFKJourneyBase):
    """Wrapper to register custom routines for AFKJourney."""

    @register_command(
        gui=GUIMetadata(
            label="Custom Routine 3",
            label_from_config="custom_routine_three.display_name",
        ),
        name="AFKJCustomRoutine3",
        kwargs={"custom_routine": "custom_routine_three"},
    )
    @register_command(
        gui=GUIMetadata(
            label="Custom Routine 2",
            label_from_config="custom_routine_two.display_name",
        ),
        name="AFKJCustomRoutine2",
        kwargs={"custom_routine": "custom_routine_two"},
    )
    @register_command(
        gui=GUIMetadata(
            label="Custom Routine 1",
            label_from_config="custom_routine_one.display_name",
        ),
        name="AFKJCustomRoutine",
        kwargs={"custom_routine": "custom_routine_one"},
    )
    def _execute(self, custom_routine: str):
        # This is used to check whether it is AFKJ Global or VN,
        # needed to restart game between Tasks if necessary.
        config = self._get_custom_routine_config(custom_routine)
        if not config.tasks:
            logging.error(
                f"{config.display_name} Tasks are empty."
                if config.display_name
                else "Tasks are empty."
            )
            return
        self.open_eyes(device_streaming=False)
        self._execute_custom_routine(config)
