import logging
from abc import ABC
from time import sleep

from adb_auto_player.exceptions import TimeoutException
from adb_auto_player.games.afk_journey.afk_journey_base import AFKJourneyBase


class AssistMixin(AFKJourneyBase, ABC):
    def assist_synergy_corrupt_creature(self) -> None:
        self.start_up(device_streaming=True)

        if self.stream is None:
            logging.warning(
                "This feature is quite slow without Device Streaming "
                "you will miss a lot of Synergy and CC requests"
            )

        assist_limit = self.get_config().general.assist_limit
        logging.info("Searching Synergy & Corrupt Creature requests in World Chat")
        count: int = 0
        while count < assist_limit:
            if self.__find_synergy_or_corrupt_creature():
                count += 1
                logging.info(f"Assist #{count}")

        logging.info("Finished: Synergy & CC")
        return None

    def __find_synergy_or_corrupt_creature(self) -> bool:
        result = self.find_any_template(
            templates=[
                "assist/label_world_chat.png",
                "assist/tap_to_enter.png",
                "assist/label_team-up_chat.png",
            ],
            crop_left=0.1,
            crop_right=0.5,
            crop_top=0.1,
            crop_bottom=0.1,
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

        profile_icon = self.find_worst_match(
            "assist/empty_chat.png",
            crop_left=0.2,
            crop_right=0.7,
            crop_top=0.7,
            crop_bottom=0.22,
        )

        if profile_icon is None:
            sleep(1)
            return False

        self.click(*profile_icon)
        try:
            self.wait_for_any_template(
                templates=[
                    "assist/join_now.png",
                    "assist/synergy.png",
                    "assist/chat_button.png",
                ],
                crop_left=0.1,
                crop_top=0.4,
                crop_bottom=0.1,
                delay=0.1,
                timeout=self.FAST_TIMEOUT,
            )
            sleep(0.5)
            template, x, y = self.wait_for_any_template(
                templates=[
                    "assist/join_now.png",
                    "assist/synergy.png",
                    "assist/chat_button.png",
                ],
                crop_left=0.1,
                crop_top=0.4,
                crop_bottom=0.1,
                delay=0.1,
                timeout=self.FAST_TIMEOUT,
            )
        except TimeoutException:
            return False
        if template == "assist/chat_button.png":
            if (
                self.find_template_match(
                    template="assist/label_world_chat.png",
                    crop_right=0.5,
                    crop_top=0.1,
                    crop_bottom=0.8,
                )
                is None
            ):
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
        ready = self.wait_for_template(
            template="assist/ready.png",
            crop_left=0.2,
            crop_right=0.1,
            crop_top=0.8,
            timeout=self.MIN_TIMEOUT,
        )

        while self.find_template_match(
            template="assist/ready.png",
            crop_left=0.2,
            crop_right=0.1,
            crop_top=0.8,
        ):
            self.click(*ready)
            sleep(0.5)

        while True:
            template, _, _ = self.wait_for_any_template(
                templates=[
                    "assist/bell.png",
                    "guide/close.png",
                    "guide/next.png",
                    "assist/label_world_chat.png",
                    "time_of_day.png",
                ],
                timeout=self.BATTLE_TIMEOUT,
            )
            logging.debug(f"template {template}")
            match template:
                case "assist/bell.png":
                    sleep(2)
                    break
                case "guide/close.png" | "guide/next.png":
                    self._handle_guide_popup()
                case _:
                    logging.debug("false")
                    logging.debug(f"template {template}")

                    return False

        logging.debug("Placing heroes")
        # click first 5 heroes in row 1 and 2
        for x in [110, 290, 470, 630, 800]:
            self.click(x, 1300, scale=True)
            sleep(0.5)
        while True:
            cc_ready = self.find_template_match(
                template="assist/cc_ready.png",
                crop_top=0.9,
                crop_left=0.1,
                crop_right=0.2,
            )
            if cc_ready:
                self.click(*cc_ready)
                sleep(1)
            else:
                break
        self.wait_for_template(
            template="assist/reward.png",
            crop_left=0.3,
            crop_right=0.3,
            crop_top=0.6,
            crop_bottom=0.3,
        )
        logging.info("Corrupt Creature done")
        self.press_back_button()
        return True

    def __handle_synergy(self) -> bool:
        go = self.find_template_match(
            template="assist/go.png",
            crop_left=0.1,
            crop_right=0.6,
            crop_top=0.7,
            crop_bottom=0.2,
        )
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
