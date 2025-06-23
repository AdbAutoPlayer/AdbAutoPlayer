from adb_auto_player.decorators import register_command
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.models.decorators import GUIMetadata


class AFKJCustomRoutine(AFKJourneyBase):
    """Wrapper to register custom routines for AFKJourney."""

    @register_command(
        gui=GUIMetadata(label="My Custom Routine"),
        name="AFKJCustomRoutine",
    )
    def _execute(self):
        self._my_custom_routine()
