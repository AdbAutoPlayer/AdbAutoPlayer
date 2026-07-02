"""Supreme Arena Mixin."""

import logging

from adb_auto_player.decorators import register_command, register_custom_routine_choice
from adb_auto_player.exceptions import GameTimeoutError
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.games.afk_journey.settings import OpponentPosition
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Point


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
            logging.debug("Tapping Challenge or Continue to enter opponent selection.")
            # Loop to dismiss any intermediate screens (reward popups, daily rewards,
            # battle-modes list, etc.) before reaching Challenge / Continue.
            btn = None
            for _ in range(5):
                btn = self.wait_for_any_template(
                    templates=[
                        "supreme_arena/challenge.png",
                        "arena/continue.png",
                        "tap_to_close.png",
                        "supreme_arena/daily_rewards.png",
                        "battle_modes/supreme_arena.png",
                    ],
                    timeout=self.min_timeout,
                    timeout_message="Failed to find Challenge or Continue button.",
                )
                if btn.template in (
                    "supreme_arena/challenge.png",
                    "arena/continue.png",
                ):
                    break
                logging.debug(f"Dismissing intermediate screen: {btn.template}")
                self.tap(btn)
                self.sleep_navigation()
            else:
                raise GameTimeoutError(
                    "Failed to reach Challenge button after dismissing popups."
                )
            self.sleep_navigation()
            self.tap(btn)
            self.sleep_navigation()

            logging.debug("Waiting for Select Opponent screen.")
            result = None
            for _ in range(5):
                result = self.wait_for_any_template(
                    templates=[
                        "supreme_arena/select_opponent.png",
                        "supreme_arena/no_attempts_popup.png",
                        "tap_to_close.png",
                        "supreme_arena/daily_rewards.png",
                    ],
                    timeout=self.min_timeout,
                    timeout_message="Failed to find Select Opponent screen.",
                )
                if result.template in (
                    "supreme_arena/select_opponent.png",
                    "supreme_arena/no_attempts_popup.png",
                ):
                    break
                logging.debug(
                    "Dismissing intermediate screen after tapping Challenge: "
                    f"{result.template}"
                )
                self.tap(result)
                self.sleep_navigation()
            else:
                raise GameTimeoutError(
                    "Failed to reach Select Opponent screen after dismissing popups."
                )

            if "no_attempts_popup" in result.template:
                logging.info(
                    "All free Supreme Arena attempts used. Declining purchase."
                )
                self.tap(Point(485, 1250))  # Tap X to cancel purchase
                return False

            position = self.settings.supreme_arena.opponent_position
            opponent_x = {
                OpponentPosition.Left: 165,
                OpponentPosition.Middle: 540,
                OpponentPosition.Right: 915,
            }[position]
            logging.debug(f"Tapping {position} opponent card.")
            self.tap(Point(opponent_x, 950))

            logging.debug("Waiting for Challenge! button on opponent detail screen.")
            challenge = self.wait_for_template(
                template="supreme_arena/challenge_detail.png",
                timeout=self.min_timeout,
                timeout_message="Failed to find Challenge! button.",
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
            self.sleep_navigation()

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
            # Dismiss any post-battle reward level popup (may appear with a short delay)
            try:
                tap_close = self.wait_for_any_template(
                    templates=["tap_to_close.png"],
                    timeout=self.fast_timeout,
                    timeout_message="No post-battle popup found.",
                )
                logging.debug("Dismissing post-battle reward popup.")
                self.tap(tap_close)
                self.sleep_navigation()
            except GameTimeoutError:
                pass
            return True
        except GameTimeoutError as fail:
            logging.error(fail)
            return False
