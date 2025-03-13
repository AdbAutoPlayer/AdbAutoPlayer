"""AFK Journey Main Module."""

from enum import StrEnum

from adb_auto_player import Command
from adb_auto_player.games.afk_journey.config import Config
from adb_auto_player.games.afk_journey.mixins import (
    AFKStagesMixin,
    ArcaneLabyrinthMixin,
    ArenaMixin,
    AssistMixin,
    DreamRealmMixin,
    DurasTrialsMixin,
    EventMixin,
    LegendTrialMixin,
)
from adb_auto_player.ipc.game_gui import GameGUIOptions, MenuOption


class ModeCategory(StrEnum):
    """Enumeration for mode categories used in the GUIs accordion menu."""

    GAME_MODES = "Game Modes"
    EVENTS_AND_OTHER = "Events & Other"


class AFKJourney(
    AFKStagesMixin,
    ArcaneLabyrinthMixin,
    AssistMixin,
    DurasTrialsMixin,
    EventMixin,
    LegendTrialMixin,
    DreamRealmMixin,
    ArenaMixin,
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
                    category=ModeCategory.GAME_MODES,
                ),
            ),
            Command(
                name="AFKStages",
                action=self.push_afk_stages,
                kwargs={"season": False},
                menu_option=MenuOption(
                    label="AFK Stages",
                    category=ModeCategory.GAME_MODES,
                ),
            ),
            Command(
                name="DurasTrials",
                action=self.push_duras_trials,
                kwargs={},
                menu_option=MenuOption(
                    label="Dura's Trials",
                    category=ModeCategory.GAME_MODES,
                ),
            ),
            Command(
                name="AssistSynergyAndCC",
                action=self.assist_synergy_corrupt_creature,
                kwargs={},
                menu_option=MenuOption(
                    label="Synergy & CC",
                    category=ModeCategory.EVENTS_AND_OTHER,
                ),
            ),
            Command(
                name="LegendTrials",
                action=self.push_legend_trials,
                kwargs={},
                menu_option=MenuOption(
                    label="Legend Trial",
                    category=ModeCategory.GAME_MODES,
                ),
            ),
            Command(
                name="ArcaneLabyrinth",
                action=self.handle_arcane_labyrinth,
                kwargs={},
                menu_option=MenuOption(
                    label="Arcane Labyrinth",
                    category=ModeCategory.GAME_MODES,
                ),
            ),
            Command(
                name="EventGuildChatClaim",
                action=self.event_guild_chat_claim,
                kwargs={},
                menu_option=MenuOption(
                    label="Guild Chat Claim",
                    category=ModeCategory.EVENTS_AND_OTHER,
                ),
            ),
            Command(
                name="EventMonopolyAssist",
                action=self.event_monopoly_assist,
                kwargs={},
                menu_option=MenuOption(
                    label="Monopoly Assist",
                    category=ModeCategory.EVENTS_AND_OTHER,
                ),
            ),
            Command(
                name="DreamRealm",
                action=self.run_dream_realm,
                kwargs={},
                menu_option=MenuOption(
                    label="Dream Realm",
                    category=ModeCategory.GAME_MODES,
                ),
            ),
            Command(
                name="Arena",
                action=self.run_arena,
                kwargs={},
                menu_option=MenuOption(
                    label="Arena",
                    category=ModeCategory.GAME_MODES,
                ),
            ),
        ]

    def get_gui_options(self) -> GameGUIOptions:
        """Get the GUI options from TOML."""
        return GameGUIOptions(
            game_title="AFK Journey",
            config_path="afk_journey/AFKJourney.toml",
            menu_options=self._get_menu_options_from_cli_menu(),
            categories=list(ModeCategory),
            constraints=Config.get_constraints(),
        )
