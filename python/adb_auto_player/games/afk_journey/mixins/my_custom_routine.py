from adb_auto_player.decorators.register_command import GuiMetadata, register_command
from adb_auto_player.games.afk_journey.base import AFKJourneyBase


class AFKJCustomRoutine(AFKJourneyBase):
    """Wrapper to register custom routines for AFKJourney."""

    @register_command(
        gui=GuiMetadata(label="My Custom Routine"),
        name="AFKJCustomRoutine",
    )
    def _execute(self):
        self._my_custom_routine()
