"""Dailies Mixin."""

import logging
from abc import ABC
from time import sleep

from adb_auto_player import Coordinates, CropRegions, GameTimeoutError
from adb_auto_player.games.afk_journey import AFKJourneyBase
from adb_auto_player.games.afk_journey.mixins.afk_stages import AFKStagesMixin
from adb_auto_player.games.afk_journey.mixins.arena import ArenaMixin
from adb_auto_player.games.afk_journey.mixins.dream_realm import DreamRealmMixin
from adb_auto_player.games.afk_journey.mixins.legend_trial import LegendTrialMixin

# from adb_auto_player.games.afk_journey.mixins import (
#     AFKStagesMixin,
#     ArenaMixin,
#     DreamRealmMixin,
#     LegendTrialMixin,
# )
# TODO: Horizontal imports cause circular imports.
# We likely need more ABCs.


class DailiesMixin(AFKJourneyBase, ABC):
    """Dailies Mixin."""

    def run_dailies(self) -> None:
        """Complete daily chores."""
        self.start_up()
        self._navigate_to_default_state()

        self.claim_daily_rewards()
        self.buy_emporium()
        self.single_pull()
        DreamRealmMixin().run_dream_realm(daily=True)  # type: ignore[abstract]
        ArenaMixin().run_arena()  # type: ignore[abstract]
        self.claim_hamburger()
        self.raise_hero_affinity()
        LegendTrialMixin().push_legend_trials()  # type: ignore[abstract]
        AFKStagesMixin().push_afk_stages(season=True)  # type: ignore[abstract]

    ############################# Daily Rewards ##############################

    def claim_daily_rewards(self) -> None:
        """Claim daily AFK rewards."""
        logging.debug("Open AFK Progress.")
        self.click(Coordinates(90, 1830), scale=True)
        sleep(1)

        logging.info("Claim AFK rewards twice for battle pass.")
        for _ in range(4):
            self.click(Coordinates(520, 1420), scale=True)
            sleep(1)

        logging.info("Looking for free hourglasses.")
        while self._claim_hourglasses():
            logging.info("Claimed a free hourglass.")

        logging.debug("Back.")
        self.press_back_button()

    def _claim_hourglasses(self) -> bool:
        """Claim free hourglass.

        Returns:
            bool: True if a free hourglass was claimed, False otherwise.
        """
        try:
            free_hourglass: tuple[int, int] = self.wait_for_template(
                "dailies/daily_rewards/free_hourglass.png",
                timeout=self.FAST_TIMEOUT,
                timeout_message="No more free hourglasses.",
            )
            self.click(Coordinates(*free_hourglass))
            sleep(2)
        except GameTimeoutError as fail:
            logging.info(fail)
            return False

        # TODO: Create a confirm do not show popup method.
        self._click_confirm_on_popup()

        self.click(Coordinates(520, 1750), scale=True)
        return True

    ############################# Mystical House ##############################

    def buy_emporium(self) -> None:
        """Purchase single pull and optionally affinity items."""
        logging.info("Entering Mystical House...")
        self.click(Coordinates(310, 1840), scale=True)

        try:
            logging.debug("Opening Emporium.")
            emporium: tuple[int, int] = self.wait_for_template(
                "dailies/emporium/emporium.png",
                timeout=self.FAST_TIMEOUT,
                timeout_message="Failed to find Emporium.",
            )
            self.click(Coordinates(*emporium))
        except GameTimeoutError as fail:
            logging.error(fail)
            return

        self._buy_single_pull()
        self._buy_affinity_items()

        logging.debug("Back to Mystical House.")
        self.press_back_button()

    def _buy_single_pull(self) -> None:
        """Buy the daily single pull."""
        logging.info("Looking for discount Invite Letter...")
        try:
            logging.debug("Opening Guild Store.")
            guild_store: tuple[int, int] = self.wait_for_template(
                "dailies/emporium/guild_store.png",
                timeout=self.FAST_TIMEOUT,
                timeout_message="Failed to find Guild Store.",
            )
            self.click(Coordinates(*guild_store))
        except GameTimeoutError as fail:
            logging.error(fail)
            return

        try:
            logging.debug("Look for discount Invite Letter.")
            invite_letter: tuple[int, int] = self.wait_for_template(
                "dailies/emporium/invite_letter.png",
                timeout=self.FAST_TIMEOUT,
                timeout_message="Discount Invite Letter already purchased.",
            )
            self.click(Coordinates(*invite_letter))

            logging.debug("Confirm purchase.")
            buy_letter: tuple[int, int] = self.wait_for_template(
                "dailies/emporium/buy_letter.png",
                timeout=self.FAST_TIMEOUT,
                timeout_message="Failed to purchase Invite Letter.",
            )
            self.click(Coordinates(*buy_letter))
        except GameTimeoutError as fail:
            logging.info(fail)

        self._click_confirm_on_popup()
        sleep(1)
        self.click(Coordinates(550, 100), scale=True)  # Close purchased window

    def _buy_affinity_items(self) -> None:
        """Buy affinity items."""
        logging.info("Looking for affinity items...")
        buy_discount: bool = self.get_config().dailies.buy_discount_affinity
        buy_all: bool = self.get_config().dailies.buy_all_affinity

        if not buy_discount and not buy_all:
            logging.info("Affinity item purchasing disabled. Skipping.")
            return

        try:
            logging.debug("Open Friendship Store.")
            friendship_store: tuple[int, int] = self.wait_for_template(
                "dailies/emporium/friendship_store.png",
                timeout=self.FAST_TIMEOUT,
                timeout_message="Failed to find Friendship Store.",
            )
            self.click(Coordinates(*friendship_store))
            sleep(1)
        except GameTimeoutError as fail:
            logging.error(fail)
            return

        logging.debug("Looking for discount affinity item.")
        discount_affinity: tuple[int, int] | None = self.game_find_template_match(
            "dailies/emporium/discount_affinity.png",
        )

        if discount_affinity:
            logging.info("Attempting to buy the discount affinity item.")
            self.click(Coordinates(*discount_affinity))
            sleep(1)
            self.click(Coordinates(600, 1780), scale=True)  # Purchase
            sleep(1)
            self.click(Coordinates(550, 100), scale=True)  # Close purchased window
            sleep(1)
        else:
            # TODO: Unreachable. Template matches even when it's grayed out (sold out).
            logging.info("Discount affinity item already purchased.")

        if not buy_all:
            logging.info("Not buying full priced affinity items.")
            return

        logging.info("Buying other affinity items.")
        other_affinity_items: list[tuple[int, int]] = self.find_all_template_matches(
            "dailies/emporium/other_affinity.png",
            crop=CropRegions(bottom=0.4),
        )

        for affinity_item in other_affinity_items:
            self.click(Coordinates(*affinity_item))
            sleep(1)
            self.click(Coordinates(600, 1780), scale=True)  # Purchase
            sleep(1)
            self.click(Coordinates(550, 100), scale=True)  # Close purchased window
            sleep(1)

    def single_pull(self) -> None:
        """Complete a single pull."""
        logging.info("Navigating to Noble Tavern for daily single pull...")
        do_single: bool = self.get_config().dailies.single_pull

        if not do_single:
            logging.info("Single pull disabled. Skipping.")
            return

        logging.info("Doing daily single pull.")
        try:
            logging.debug("Opening Noble Tavern.")
            tavern: tuple[int, int] = self.wait_for_template(
                "dailies/noble_tavern/noble_tavern.png",
                timeout=self.FAST_TIMEOUT,
                timeout_message="Failed to find the Noble Tavern.",
            )
            self.click(Coordinates(*tavern))
            sleep(2)

            logging.debug("Select All-Hero Recruitment.")
            all_hero_recruit: tuple[int, int] = self.wait_for_template(
                "dailies/noble_tavern/all_hero_recruit.png",
                timeout=self.FAST_TIMEOUT,
                timeout_message="Failed to find All-Hero Recruitment.",
            )
            self.click(Coordinates(*all_hero_recruit))
            sleep(2)

            logging.debug("Click Recruit 1.")
            recruit: tuple[int, int] = self.wait_for_template(
                "dailies/noble_tavern/recruit.png",
                timeout=self.FAST_TIMEOUT,
                timeout_message="No Invite Letters.",
            )
            self.click(Coordinates(*recruit))
            sleep(2)

            max_hero_continue: tuple[int, int] | None = self.game_find_template_match(
                "dailies/noble_tavern/maxed_hero_continue.png"
            )
            if max_hero_continue:
                logging.debug("Dismiss max hero warning.")
                self.click(Coordinates(*max_hero_continue))

            logging.debug("Wait for back button.")
            confirm_summon: tuple[int, int] = self.wait_for_template(
                "back.png",
                timeout=self.MIN_TIMEOUT,
                timeout_message="Failed to recruit.",
            )
            self.click(Coordinates(*confirm_summon))
            sleep(2)
        except GameTimeoutError as fail:
            logging.error(fail)

        logging.debug("Back.")
        self.press_back_button()

    ############################# Hamburger Rewards ##############################

    def claim_hamburger(self) -> None:
        """Claim rewards from hamburger menu."""
        self._navigate_to_default_state()

        logging.info("Navigating to Hamburger.")
        self.click(Coordinates(990, 1840), scale=True)
        sleep(1)

        self._claim_friend_rewards()
        self._claim_mail()
        self._claim_battle_pass()
        self._claim_quests()

    def _claim_friend_rewards(self) -> None:
        """Claim friend rewards."""
        logging.info("Claiming friend rewards.")
        try:
            logging.debug("Click Friends.")
            friends: tuple[int, int] = self.wait_for_template(
                "dailies/hamburger/friends.png",
                timeout=self.MIN_TIMEOUT,
                timeout_message="Failed to find Friends. Sadge.",
            )
            self.click(Coordinates(*friends))
            sleep(1)

            logging.debug("Click Send & Receive.")
            send_receive: tuple[int, int] = self.wait_for_template(
                "dailies/hamburger/send_receive.png",
                timeout=self.FAST_TIMEOUT,
                timeout_message="Friend rewards already claimed.",
            )
            self.click(Coordinates(*send_receive))
            sleep(2)
            self.click(Coordinates(540, 1620))  # Close confirmation
            sleep(1)
        except GameTimeoutError as fail:
            logging.info(fail)

        logging.debug("Back.")  # TODO: Create generic back method.
        back: tuple[int, int] | None = self.game_find_template_match("back.png")
        self.click(Coordinates(*back)) if back else self.press_back_button()

    def _claim_mail(self) -> None:
        """Claim mail."""
        logging.info("Claiming Mail.")
        try:
            logging.debug("Click Mail.")
            mail: tuple[int, int] = self.wait_for_template(
                "dailies/hamburger/mail.png",
                timeout=self.MIN_TIMEOUT,
                timeout_message="Failed to find Mail.",
            )
            self.click(Coordinates(*mail))
            sleep(1)
        except GameTimeoutError as fail:
            logging.error(fail)
            return

        try:
            logging.debug("Click Read All.")
            read_all: tuple[int, int] = self.wait_for_template(
                "dailies/hamburger/read_all.png",
                timeout=self.FAST_TIMEOUT,
                timeout_message="No mail.",
            )
            self.click(Coordinates(*read_all))
            sleep(1)
            self.click(Coordinates(540, 1620))  # Close confirmation
            sleep(1)
        except GameTimeoutError as fail:
            logging.info(fail)

        logging.debug("Back.")
        back: tuple[int, int] | None = self.game_find_template_match("back.png")
        self.click(Coordinates(*back)) if back else self.press_back_button()

    def _claim_battle_pass(self) -> None:
        """Claim Battle Pass rewards."""
        logging.info("Claim Battle Pass rewards.")
        try:
            logging.debug("Click Noble Path.")
            battle_pass: tuple[int, int] = self.wait_for_template(
                "dailies/hamburger/battle_pass.png",
                timeout=self.MIN_TIMEOUT,
                timeout_message="Failed to find Battle Pass.",
            )
            self.click(Coordinates(*battle_pass))
            sleep(2)
        except GameTimeoutError as fail:
            logging.error(fail)
            return

        logging.debug("Looking for available rewards.")
        available_rewards: list[tuple[int, int]] = self.find_all_template_matches(
            "dailies/hamburger/rewards_available.png", crop=CropRegions(top=0.8)
        )
        for bp_reward in available_rewards:
            self.click(Coordinates(*bp_reward))
            sleep(2)
            self._quick_claim()
            sleep(1)

        logging.debug("Back.")
        back: tuple[int, int] | None = self.game_find_template_match("back.png")
        self.click(Coordinates(*back)) if back else self.press_back_button()

    def _claim_quests(self) -> None:
        """Claim Quest rewards."""
        logging.info("Claim Quest rewards.")
        try:
            logging.debug("Click Quests.")
            quests: tuple[int, int] = self.wait_for_template(
                "dailies/hamburger/quests.png",
                timeout=self.MIN_TIMEOUT,
                timeout_message="Failed to find daily Quests.",
            )
            self.click(Coordinates(*quests))
            sleep(2)
        except GameTimeoutError as fail:
            logging.error(fail)
            return

        logging.info("Claim Daily Quest rewards.")
        self._quick_claim()
        self.click(Coordinates(370, 180))  # Claim top row
        sleep(2)
        self.click(Coordinates(530, 1740))  # Close confirmation
        sleep(2)

        logging.info("Claim Guild Quest rewards.")
        self.click(Coordinates(830, 1670))  # Guild Quests
        sleep(2)
        self._quick_claim()

    def _quick_claim(self) -> None:
        logging.debug("Click Quick Claim.")
        claim: tuple[int, int] | None = self.game_find_template_match(
            "dailies/hamburger/quick_claim.png",
        )
        if not claim:
            return

        self.click(Coordinates(*claim))
        sleep(2)
        self.click(Coordinates(540, 1620))  # Close confirmation
        sleep(2)

    ############################# Hero Affinity ##############################

    def raise_hero_affinity(self) -> None:
        """Raise hero affinity with 3 clicks per day."""
        self._navigate_to_default_state()

        logging.debug("Open Resonating Hall.")
        self.click(Coordinates(620, 1830), scale=True)
        sleep(1)

        logging.info("Begin raising hero affinity.")
        self.click(Coordinates(130, 1040), scale=True)
        sleep(1)

        while not self.game_find_template_match("dailies/resonating_hall/chippy.png"):
            self._click_hero()
            sleep(1)
        self._click_hero()  # Give Chippy some love too.

        logging.info("Done raising affinity.")

    def _click_hero(self) -> None:
        """Click a hero for affinity and go next."""
        back: tuple[int, int] | None = self.game_find_template_match("back.png")
        back_button: Coordinates = (
            Coordinates(*back) if back else Coordinates(100, 1800)
        )

        for _ in range(3):
            # NOTE: Sometimes spam click works and other times not.
            # So we go with the safe route of click then back.
            self.click(Coordinates(540, 840), scale=True)
            sleep(0.5)
            self.click(back_button, scale=True)
            sleep(0.5)

        self.click(Coordinates(995, 1090), scale=True)  # Next hero
