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
from adb_auto_player.ipc.game_gui import GameGUIOptions, MenuOption


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
                action=self.push_afk_stages,
                kwargs={"season": True},
                menu_option=MenuOption(
                    label="Season Talent Stages",
                    category="Game Modes",
                ),
            ),
            Command(
                name="AFKStages",
                action=self.push_afk_stages,
                kwargs={"season": False},
                menu_option=MenuOption(
                    label="AFK Stages",
                    category="Game Modes",
                ),
            ),
            Command(
                name="DurasTrials",
                action=self.push_duras_trials,
                kwargs={},
                menu_option=MenuOption(
                    label="Dura's Trials",
                    category="Game Modes",
                ),
            ),
            Command(
                name="AssistSynergyAndCC",
                action=self.assist_synergy_corrupt_creature,
                kwargs={},
                menu_option=MenuOption(
                    label="Synergy & CC",
                    category="Events & Other",
                ),
            ),
            Command(
                name="LegendTrials",
                action=self.push_legend_trials,
                kwargs={},
                menu_option=MenuOption(
                    label="Legend Trial",
                    category="Game Modes",
                ),
            ),
            Command(
                name="ArcaneLabyrinth",
                action=self.handle_arcane_labyrinth,
                kwargs={},
                menu_option=MenuOption(
                    label="Arcane Labyrinth",
                    category="Game Modes",
                ),
            ),
            Command(
                name="EventGuildChatClaim",
                action=self.event_guild_chat_claim,
                kwargs={},
                menu_option=MenuOption(
                    label="Guild Chat Claim",
                    category="Events & Other",
                ),
            ),
            Command(
                name="EventMonopolyAssist",
                action=self.event_monopoly_assist,
                kwargs={},
                menu_option=MenuOption(
                    label="Monopoly Assist",
                    category="Events & Other",
                ),
            ),
        ]

    def get_gui_options(self) -> GameGUIOptions:
        """Get the GUI options from TOML."""
        return GameGUIOptions(
            game_title="AFK Journey",
            config_path="afk_journey/AFKJourney.toml",
            menu_options=self._get_menu_options_from_cli_menu(),
            categories=["Game Modes", "Events & Other"],
            constraints=Config.get_constraints(),
        )
