"""Supreme Arena Mixin."""

import logging

from adb_auto_player.decorators import register_command, register_custom_routine_choice
from adb_auto_player.exceptions import GameTimeoutError
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models.decorators import GUIMetadata


class SupremeArenaMixin(AFKJourneyBase):
    """Supreme Arena Mixin."""

    @register_command(
        name="SupremeArena",
        gui=GUIMetadata(
            label="Supreme Arena",
            category=AFKJCategory.GAME_MODES,
            tooltip="Participate in daily Supreme Arena battles automatically",
        ),
    )
    @register_custom_routine_choice(label="Supreme Arena")
    def run_supreme_arena(self) -> None:
        """Use Supreme Arena attempts."""
        self.start_up(device_streaming=False)

        try:
            self._enter_supreme_arena()
        except GameTimeoutError:
            return

        for _ in range(self.settings.supreme_arena.attempts):
            if self.game_find_template_match("arena/no_attempts.png"):
                logging.info("No more Supreme Arena challenges available.")
                break

            if not self._sa_choose_opponent():
                break
            if not self._sa_battle():
                break

        logging.info("Supreme Arena finished.")

    ############################## Helper Functions ##############################

    def _enter_supreme_arena(self) -> None:
        """Enter Supreme Arena."""
        logging.info("Entering Supreme Arena...")
        self.navigate_to_battle_modes_screen()
        try:
            mode = self._find_in_battle_modes(
                "battle_modes/supreme_arena.png",
                "Failed to find Supreme Arena.",
            )
            self.tap(mode)
            self.sleep_navigation()
        except GameTimeoutError as fail:
            logging.error(f"{fail} {self.LANG_ERROR}")
            raise

    def _sa_choose_opponent(self) -> bool:
        """Challenge and choose the weakest (leftmost) Supreme Arena opponent.

        Returns:
            bool: True if opponent chosen and challenge confirmed, False otherwise.
        """
        try:
            logging.debug("Tapping Challenge to enter opponent selection.")
            btn = self.wait_for_template(
                template="supreme_arena/challenge.png",
                timeout=self.min_timeout,
                timeout_message="Failed to find Challenge button.",
            )
            self.sleep_navigation()
            self.tap(btn)

            logging.debug("Selecting leftmost opponent via Challenge button.")
            challenge = self.wait_for_template(
                template="supreme_arena/challenge.png",
                timeout=self.min_timeout,
                timeout_message="Failed to find opponent Challenge button.",
            )
            self.tap(challenge)
            return True
        except GameTimeoutError as fail:
            logging.error(fail)
            return False

    def _sa_battle(self) -> bool:
        """Execute the Supreme Arena battle: Next, Next, Battle, wait for end.

        Returns:
            bool: True if battle completed, False otherwise.
        """
        try:
            logging.debug("Tapping Next (1/2).")
            next1 = self.wait_for_template(
                template="next.png",
                timeout=self.min_timeout,
                timeout_message="Failed to find Next button (1/2).",
            )
            self.tap(next1)

            logging.debug("Tapping Next (2/2).")
            next2 = self.wait_for_template(
                template="next.png",
                timeout=self.min_timeout,
                timeout_message="Failed to find Next button (2/2).",
            )
            self.tap(next2)

            logging.debug("Starting battle.")
            battle = self.wait_for_template(
                template="arena/battle.png",
                timeout=self.min_timeout,
                timeout_message="Failed to find Battle button.",
            )
            self.sleep_navigation()
            self.tap(battle)

            logging.debug("Waiting for battle to complete.")
            # Try to skip if available
            try:
                skip = self.wait_for_template(
                    template="arena/skip.png",
                    timeout=self.min_timeout,
                    timeout_message="No skip button found.",
                )
                self.tap(skip)
            except GameTimeoutError:
                pass

            self.handle_popup_messages()
            done = self.wait_for_any_template(
                templates=["arena/done.png", "next.png", "navigation/confirm.png"],
                timeout=self.BATTLE_TIMEOUT,
                timeout_message="Battle did not complete in time.",
            )
            self.sleep_navigation()
            self.tap(done)
            self.sleep_navigation()
            return True
        except GameTimeoutError as fail:
            logging.error(fail)
            return False
