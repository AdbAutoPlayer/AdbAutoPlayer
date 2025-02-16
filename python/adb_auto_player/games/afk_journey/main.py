from adb_auto_player.command import Command

from adb_auto_player.games.afk_journey.mixins.afk_stages import AFKStagesMixin
from adb_auto_player.games.afk_journey.mixins.assist import AssistMixin
from adb_auto_player.games.afk_journey.config import Config
from adb_auto_player.games.afk_journey.mixins.duras_trials import DurasTrialsMixin
from adb_auto_player.games.afk_journey.mixins.event import EventMixin
from adb_auto_player.games.afk_journey.mixins.legend_trial import LegendTrialMixin
from adb_auto_player.ipc.game_gui import GameGUIOptions


class AFKJourney(
    AFKStagesMixin,
    AssistMixin,
    DurasTrialsMixin,
    EventMixin,
    LegendTrialMixin,
):
    def get_cli_menu_commands(self) -> list[Command]:
        # Add new commands/gui buttons here
        return [
            Command(
                name="SeasonTalentStages",
                gui_label="Season Talent Stages",
                action=self.push_afk_stages,
                kwargs={"season": True},
            ),
            Command(
                name="AFKStages",
                gui_label="AFK Stages",
                action=self.push_afk_stages,
                kwargs={"season": False},
            ),
            Command(
                name="DurasTrials",
                gui_label="Dura's Trials",
                action=self.push_duras_trials,
                kwargs={},
            ),
            Command(
                name="AssistSynergyAndCC",
                gui_label="Synergy & CC",
                action=self.assist_synergy_corrupt_creature,
                kwargs={},
            ),
            Command(
                name="LegendTrials",
                gui_label="Legend Trial",
                action=self.push_legend_trials,
                kwargs={},
            ),
            Command(
                name="EventGuildChatClaim",
                gui_label="[Event] Guild Chat Claim",
                action=self.event_guild_chat_claim,
                kwargs={},
            ),
            Command(
                name="EventMonopolyAssist",
                gui_label="[Event] Monopoly Assist",
                action=self.event_monopoly_assist,
                kwargs={},
            ),
        ]

    def get_gui_options(self) -> GameGUIOptions:
        return GameGUIOptions(
            game_title="AFK Journey",
            config_path="afk_journey/AFKJourney.toml",
            menu_options=self._get_menu_options_from_cli_menu(),
            constraints=Config.get_constraints(),
        )
