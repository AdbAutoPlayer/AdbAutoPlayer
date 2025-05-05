"""AFK Journey Main Module."""

import datetime
import logging
import sys
from enum import StrEnum
from time import sleep

from adb_auto_player import Command
from adb_auto_player.exceptions import GameNotRunningError
from adb_auto_player.games.afk_journey.config import Config
from adb_auto_player.games.afk_journey.mixins import (
    AFKStagesMixin,
    ArcaneLabyrinthMixin,
    ArenaMixin,
    AssistMixin,
    DailiesMixin,
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
    WIP_PLEASE_TEST = "WIP Please Test"


class AFKJourney(
    AFKStagesMixin,
    ArcaneLabyrinthMixin,
    AssistMixin,
    DurasTrialsMixin,
    EventMixin,
    LegendTrialMixin,
    DreamRealmMixin,
    ArenaMixin,
    DailiesMixin,
):
    """AFK Journey Game."""

    def get_cli_menu_commands(self) -> list[Command]:
        """Get the CLI menu commands."""
        # Add new commands/gui buttons here
        return [
            Command(
                name="Dailies",
                action=self.run_dailies,
                menu_option=MenuOption(
                    label="Dailies",
                    category=ModeCategory.GAME_MODES,
                ),
            ),
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
                menu_option=MenuOption(
                    label="Dura's Trials",
                    category=ModeCategory.GAME_MODES,
                ),
            ),
            Command(
                name="AssistSynergyAndCC",
                action=self.assist_synergy_corrupt_creature,
                menu_option=MenuOption(
                    label="Synergy & CC",
                    category=ModeCategory.EVENTS_AND_OTHER,
                ),
            ),
            Command(
                name="LegendTrials",
                action=self.push_legend_trials,
                menu_option=MenuOption(
                    label="Legend Trial",
                    category=ModeCategory.GAME_MODES,
                ),
            ),
            Command(
                name="ArcaneLabyrinth",
                action=self.handle_arcane_labyrinth,
                menu_option=MenuOption(
                    label="Arcane Labyrinth",
                    category=ModeCategory.GAME_MODES,
                ),
            ),
            Command(
                name="DreamRealm",
                action=self.run_dream_realm,
                menu_option=MenuOption(
                    label="Dream Realm",
                    category=ModeCategory.GAME_MODES,
                ),
            ),
            Command(
                name="Arena",
                action=self.run_arena,
                menu_option=MenuOption(
                    label="Arena",
                    category=ModeCategory.GAME_MODES,
                ),
            ),
            Command(
                name="EventGuildChatClaim",
                action=self.event_guild_chat_claim,
                menu_option=MenuOption(
                    label="Guild Chat Claim",
                    category=ModeCategory.EVENTS_AND_OTHER,
                ),
                allow_in_my_custom_routine=False,
            ),
            Command(
                name="EventMonopolyAssist",
                action=self.event_monopoly_assist,
                menu_option=MenuOption(
                    label="Monopoly Assist",
                    category=ModeCategory.EVENTS_AND_OTHER,
                ),
                allow_in_my_custom_routine=False,
            ),
            Command(
                name="AFKJCustomRoutine",
                action=self._my_custom_routine,
                menu_option=MenuOption(
                    label="My Custom Routine",
                    category=ModeCategory.WIP_PLEASE_TEST,  # TODO update
                ),
                allow_in_my_custom_routine=False,
            ),
        ]

    def get_gui_options(self) -> GameGUIOptions:
        """Get the GUI options from TOML."""
        menu_options = self._get_menu_options_from_cli_menu()
        return GameGUIOptions(
            game_title="AFK Journey",
            config_path="afk_journey/AFKJourney.toml",
            menu_options=menu_options,
            categories=list(ModeCategory),
            constraints=Config.get_constraints(commands=self.get_cli_menu_commands()),
        )

    def _my_custom_routine(self) -> None:
        config = self.get_config().my_custom_routine
        if not config.daily_tasks and not config.repeating_tasks:
            logging.error(
                'You need to set Tasks in the Game Config "My Custom Routine" Section'
            )
            return
        # Needs to start with Device Streaming.
        # If the first action does not start with device streaming
        # but the second requires it, device streaming will not be initialized
        # because the device is already initialized
        # self.start_up(device_streaming=True)

        daily_tasks_executed_at = datetime.datetime.now(datetime.UTC)
        if config.daily_tasks:
            if config.skip_daily_tasks_today:
                logging.warning("Skipping daily tasks today")
            else:
                logging.info("Executing Daily Tasks")
                self._execute_tasks(config.daily_tasks)
        else:
            logging.info("No Daily Tasks, skipping")

        while True:
            logging.info("Executing Repeating Tasks")
            if config.repeating_tasks:
                self._execute_tasks(config.repeating_tasks)
            else:
                logging.warning("No Repeating Tasks, waiting for next day")
                sleep(180)

            now = datetime.datetime.now(datetime.UTC)
            if now.date() != daily_tasks_executed_at.date():
                logging.info("Executing Daily Tasks")
                self._execute_tasks(config.daily_tasks)
                daily_tasks_executed_at = now
            else:
                next_day = datetime.datetime.combine(
                    now.date() + datetime.timedelta(days=1),
                    datetime.time.min,
                    tzinfo=datetime.UTC,
                )
                remaining = next_day - now
                hours, remainder = divmod(remaining.seconds, 3600)
                minutes = remainder // 60
                logging.info(
                    f"Time until next Daily Task execution: {hours}h {minutes}m"
                )
        logging.error("Not Implemented :)")
        return

    def _execute_tasks(self, tasks: list[str]) -> None:
        commands = self.get_cli_menu_commands()

        for task in tasks:
            command: Command | None = None
            for cmd in commands:
                if not cmd.allow_in_my_custom_routine:
                    continue
                if task in (cmd.menu_option.label, cmd.name):
                    command = cmd
                    break
            if not command:
                logging.error(f"Task '{task}' not found")
                continue
            error = command.run()
            if isinstance(error, GameNotRunningError):
                self.package_name = "test"
                if self.package_name:
                    logging.warning(
                        f"Task '{task}' failed because the game is not running, "
                        f"attempting to restart it."
                    )
                    self.start_game()
                    sleep(5)
                else:
                    logging.error(
                        f"Task '{task}' failed because the game is not running"
                    )
                    sys.exit(1)
                continue
