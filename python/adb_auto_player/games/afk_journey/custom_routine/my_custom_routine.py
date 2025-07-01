from adb_auto_player.decorators import register_command
from adb_auto_player.models.decorators import GUIMetadata

from ..base import AFKJourneyBase


class AFKJCustomRoutine(AFKJourneyBase):
    """Wrapper to register custom routines for AFKJourney."""

    @register_command(
        gui=GUIMetadata(label="My Custom Routine"),
        name="AFKJCustomRoutine",
    )
    def _execute(self):
        # This is used to check whether it is AFKJ Global or VN,
        # needed to restart game between Tasks if necessary.
        self.open_eyes(device_streaming=False)
        self._my_custom_routine()
