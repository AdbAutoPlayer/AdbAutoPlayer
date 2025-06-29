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
        self._my_custom_routine()
