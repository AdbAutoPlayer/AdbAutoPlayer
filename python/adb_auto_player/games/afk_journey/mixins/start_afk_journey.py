from adb_auto_player.decorators.register_command import register_command
from adb_auto_player.games.afk_journey.base import AFKJourneyBase


class StartAFKJourney(AFKJourneyBase):
    @register_command(
        gui=None,  # explicitly putting this here we do not want a GUI Button for this.
        name="AFKJStartGame",
    )
    def start_afk_journey(self) -> None:
        # Could have a checkbox in the settings to derive whether the default
        # should be global or .vn
        # if yes set it at the start of start_up()
        # worse alternative: check if only one of the 2 versions is installed
        # can be done via adb by getting the list of installed apps
        # and start the installed version
        # but what do you do when both are installed?

        # vn com.farlightgames.igame.gp.vn
        self.package_name = "com.farlightgames.igame.gp"  # global
        self.start_up(device_streaming=False)
        self.start_game()
