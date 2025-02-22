import logging
from abc import ABC
from time import sleep

from adb_auto_player.games.afk_journey.afk_journey_base import AFKJourneyBase


class DurasTrialsMixin(AFKJourneyBase, ABC):
    def push_duras_trials(self) -> None:
        self.start_up()
        self.store[self.STORE_MODE] = self.MODE_DURAS_TRIALS
        self.__navigate_to_duras_trials_screen()

        self.wait_for_template("duras_trials/rate_up.png", grayscale=True)
        rate_up_banners = self.find_all_template_matches(
            "duras_trials/rate_up.png", grayscale=True, use_previous_screenshot=True
        )

        if not rate_up_banners:
            logging.warning(
                "Dura's Trials Rate Up banners could not be found, Stopping"
            )
            return None

        first_banner = True
        for banner in rate_up_banners:
            if not first_banner:
                self.__navigate_to_duras_trials_screen()
            self.__handle_dura_screen(*banner)
            self.__navigate_to_duras_trials_screen()
            self.__handle_dura_screen(*banner, nightmare_mode=True)
            first_banner = False

        return None

    def __navigate_to_duras_trials_screen(self) -> None:
        logging.info("Navigating to Dura's Trial select")

        def check_for_duras_trials_label() -> bool:
            match = self.find_template_match("duras_trials/featured_heroes.png")
            return match is not None

        self._navigate_to_default_state(check_callable=check_for_duras_trials_label)

        featured_heroes = self.find_template_match(
            "duras_trials/featured_heroes.png",
            use_previous_screenshot=True,
        )
        if featured_heroes is not None:
            return

        logging.info("Clicking Battle Modes button")
        self.click(460, 1830, scale=True)
        duras_trials_label = self.wait_for_template("duras_trials/label.png")
        self.click(*duras_trials_label)
        self.wait_for_template("duras_trials/featured_heroes.png")
        return None

    def __dura_resolve_state(self) -> tuple[str, int, int]:
        while True:
            template, x, y = self.wait_for_any_template(
                templates=[
                    "battle/records.png",
                    "duras_trials/battle.png",
                    "duras_trials/sweep.png",
                    "guide/close.png",
                    "guide/next.png",
                ],
            )

            match template:
                case "guide/close.png" | "guide/next.png":
                    self._handle_guide_popup(use_previous_screenshot=True)
                case _:
                    break
        return template, x, y

    def __handle_dura_screen(
        self, x: int, y: int, nightmare_mode: bool = False
    ) -> None:
        # y+100 clicks closer to center of the button instead of rate up text
        offset = int(self.get_scale_factor() * 100)
        self.click(x, y + offset)

        count: int = 0
        while True:
            template, _, _ = self.__dura_resolve_state()

            if nightmare_mode and template != "battle/records.png":
                nightmare = self.find_template_match("duras_trials/nightmare.png")
                if nightmare is None:
                    logging.warning("Nightmare Button not found")
                    return None
                self.click(*nightmare)
                template, x, y = self.wait_for_any_template(
                    [
                        "duras_trials/nightmare_skip.png",
                        "duras_trials/nightmare_swords.png",
                        "duras_trials/cleared.png",
                    ]
                )
                match template:
                    case "duras_trials/nightmare_skip.png":
                        self.click(x, y)
                        self.wait_until_template_disappears(
                            "duras_trials/nightmare_skip.png"
                        )
                        # clicks the reward popup
                        self.click(x, y)
                        self.wait_for_template("duras_trials/nightmare_swords.png")
                        self.click(x, y)
                    case "duras_trials/nightmare_swords.png":
                        self.click(x, y)
                    case "duras_trials/cleared.png":
                        logging.info("Nightmare Trial already cleared")
                        return None
            else:
                template, x, y = self.__dura_resolve_state()
                match template:
                    case "duras_trials/sweep.png":
                        logging.info("Dura's Trial already cleared")
                        return None
                    case "duras_trials/battle.png":
                        self.click(x, y)
                    case "battle/records.png":
                        pass

            result = self._handle_battle_screen(
                self.get_config().duras_trials.use_suggested_formations
            )

            if result is True and not nightmare_mode:
                self.wait_for_template("duras_trials/first_clear.png")
                next_button = self.find_template_match("next.png")
                if next_button is not None:
                    count += 1
                    logging.info(f"Trials pushed: {count}")
                    self.click(*next_button)
                    self.click(*next_button)
                    sleep(3)
                    continue
                else:
                    logging.info("Dura's Trial completed")
                    return None

            if result is True and nightmare_mode:
                count += 1
                logging.info(f"Nightmare Trials pushed: {count}")
                if self.find_template_match("duras_trials/continue_gray.png"):
                    logging.info("Nightmare Trial completed")
                    return None
                continue
            logging.info("Dura's Trial failed")
            return None
        return None
