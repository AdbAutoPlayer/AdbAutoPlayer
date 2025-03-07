"""AFK Journey Main Module."""

from adb_auto_player import Command
from adb_auto_player.games.afk_journey.config import Config
from adb_auto_player.games.afk_journey.mixins import (
    AFKStagesMixin,
    ArcaneLabyrinthMixin,
    AssistMixin,
    DurasTrialsMixin,
    EventMixin,
    LegendTrialMixin,
)
from adb_auto_player.ipc.game_gui import GameGUIOptions


class AFKJourney(
    AFKStagesMixin,
    ArcaneLabyrinthMixin,
    AssistMixin,
    DurasTrialsMixin,
    EventMixin,
    LegendTrialMixin,
):
    """AFK Journey Game."""

    def get_cli_menu_commands(self) -> list[Command]:
        """Get the CLI menu commands."""
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
                name="ArcaneLabyrinth",
                gui_label="Arcane Labyrinth",
                action=self.handle_arcane_labyrinth,
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
        """Get the GUI options from TOML."""
        return GameGUIOptions(
            game_title="AFK Journey",
            config_path="afk_journey/AFKJourney.toml",
            menu_options=self._get_menu_options_from_cli_menu(),
            constraints=Config.get_constraints(),
        )
