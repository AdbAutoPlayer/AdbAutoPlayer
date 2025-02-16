import logging
from abc import ABC
from time import sleep

from adb_auto_player.exceptions import TimeoutException
from adb_auto_player.games.afk_journey.afk_journey_base import AFKJourneyBase


class AssistMixin(AFKJourneyBase, ABC):
    def assist_synergy_corrupt_creature(self) -> None:
        self.start_up()
        assist_limit = self.get_config().general.assist_limit
        logging.info("Running: Synergy & CC")
        count: int = 0
        while count < assist_limit:
            logging.info("Searching Synergy & Corrupt Creature requests in World Chat")
            if self.__find_synergy_or_corrupt_creature():
                count += 1
                logging.info(f"Assist #{count}")

        logging.info("Finished: Synergy & CC")
        return None

    def __find_synergy_or_corrupt_creature(self) -> bool:
        result = self.find_any_template(
            [
                "assist/label_world_chat.png",
                "assist/tap_to_enter.png",
                "assist/label_team-up_chat.png",
            ]
        )
        if result is None:
            logging.info("Navigating to World Chat")
            self._navigate_to_default_state()
            self.click(1010, 1080, scale=True)
            sleep(1)
            self.click(110, 350, scale=True)
            return False

        template, x, y = result
        match template:
            # Chat Window is open but not on World Chat
            case "assist/tap_to_enter.png", "assist/label_team-up_chat.png":
                logging.info("Switching to World Chat")
                self.click(110, 350, scale=True)
                return False
            case "assist/label_world_chat.png":
                pass
        # Click Profile icon in chat
        self.click(260, 1400, scale=True)
        try:
            template, x, y = self.wait_for_any_template(
                ["assist/join_now.png", "assist/synergy.png", "assist/chat_button.png"],
                delay=0.1,
                timeout=self.FAST_TIMEOUT,
            )
        except TimeoutException:
            return False
        if "assist/chat_button.png" == template:
            if self.find_template_match("assist/label_world_chat.png") is None:
                # Back button does not always close profile/chat windows
                self.click(550, 100, scale=True)
                sleep(1)
            return False
        self.click(x, y)
        match template:
            case "assist/join_now.png":
                logging.info("Clicking Corrupt Creature join now button")
                try:
                    return self.__handle_corrupt_creature()
                except TimeoutException:
                    logging.warning(
                        "Clicked join now button too late or something went wrong"
                    )
                    return False
            case "assist/synergy.png":
                logging.info("Clicking Synergy button")
                return self.__handle_synergy()
        return False

    def __handle_corrupt_creature(self) -> bool:
        ready = self.wait_for_template("assist/ready.png", timeout=self.MIN_TIMEOUT)

        self.click(*ready)
        # Sometimes people wait forever for a third to join...
        self.wait_until_template_disappears(
            "assist/rewards_heart.png", timeout=self.BATTLE_TIMEOUT
        )
        self.wait_for_template("assist/bell.png")
        # click first 5 heroes in row 1 and 2
        for x in [110, 290, 470, 630, 800]:
            self.click(x, 1300, scale=True)
            sleep(0.5)
        while True:
            cc_ready = self.find_template_match("assist/cc_ready.png")
            if cc_ready:
                self.click(*cc_ready)
                sleep(1)
            else:
                break
        self.wait_for_template("assist/reward.png")
        logging.info("Corrupt Creature done")
        self.press_back_button()
        return True

    def __handle_synergy(self) -> bool:
        go = self.find_template_match("assist/go.png")
        if go is None:
            logging.info("Clicked Synergy button too late")
            return False
        self.click(*go)
        sleep(3)
        self.click(130, 900, scale=True)
        sleep(1)
        self.click(630, 1800, scale=True)
        logging.info("Synergy complete")
        return True
