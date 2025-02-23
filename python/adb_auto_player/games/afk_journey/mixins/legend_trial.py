import logging
from abc import ABC
from time import sleep

from adb_auto_player.exceptions import TimeoutException, NotFoundException
from adb_auto_player.games.afk_journey.afk_journey_base import AFKJourneyBase


class LegendTrialMixin(AFKJourneyBase, ABC):
    def push_legend_trials(self) -> None:
        self.start_up()
        self.store[self.STORE_MODE] = self.MODE_LEGEND_TRIALS
        try:
            self.__navigate_to_legend_trials_select_tower()
        except TimeoutException as e:
            logging.error(f"{e}")
            return None

        towers = self.get_config().legend_trials.towers

        results = {}
        factions = [
            "lightbearer",
            "wilder",
            "graveborn",
            "mauler",
        ]
        sleep(1)
        self.get_screenshot()
        for faction in factions:
            if faction.capitalize() not in towers:
                logging.info(f"{faction.capitalize()}s excluded in config")
                continue

            if self.find_template_match(
                template=f"legend_trials/faction_icon_{faction}.png",
                crop_right=0.7,
                crop_top=0.3,
                crop_bottom=0.1,
                use_previous_screenshot=True,
            ):
                logging.warning(f"{faction.capitalize()} Tower not available today")
                continue

            result = self.find_template_match(
                template=f"legend_trials/banner_{faction}.png",
                crop_left=0.2,
                crop_right=0.3,
                crop_top=0.2,
                crop_bottom=0.1,
                use_previous_screenshot=True,
            )
            if result is None:
                logging.error(f"{faction.capitalize()}s Tower not found")
            else:
                results[faction] = result

        for faction, result in results.items():
            logging.info(f"Starting {faction.capitalize()} Tower")
            if self.find_template_match(
                template=f"legend_trials/faction_icon_{faction}.png",
                crop_right=0.7,
                crop_top=0.3,
                crop_bottom=0.1,
            ):
                logging.warning(f"{faction.capitalize()} Tower no longer available")
                continue
            self.__navigate_to_legend_trials_select_tower()
            self.click(*result)
            try:
                self.__select_legend_trials_floor(faction)
            except (TimeoutException, NotFoundException) as e:
                logging.error(f"{e}")
                self.press_back_button()
                sleep(3)
                continue
            self.__handle_legend_trials_battle(faction)
        logging.info("Legend Trial finished")
        return None

    def __handle_legend_trials_battle(self, faction: str) -> None:
        count: int = 0
        while True:
            try:
                result = self._handle_battle_screen(
                    self.get_config().legend_trials.use_suggested_formations
                )
            except TimeoutException as e:
                logging.warning(f"{e}")
                return None

            if result is True:
                next_btn = self.wait_for_template(
                    template="next.png",
                    crop_left=0.6,
                    crop_top=0.9,
                )
                if next_btn is not None:
                    count += 1
                    logging.info(f"{faction.capitalize()} Trials pushed: {count}")
                    self.click(*next_btn)
                    continue
                else:
                    logging.warning(
                        "Not implemented assuming this shows up after the last floor?"
                    )
                    return None
            logging.info(f"{faction.capitalize()} Trials failed")
            return None
        return None

    def __select_legend_trials_floor(self, faction: str) -> None:
        logging.debug("__select_legend_trials_floor")
        _ = self.wait_for_template(
            template=f"legend_trials/tower_icon_{faction}.png",
            crop_right=0.8,
            crop_bottom=0.8,
        )
        challenge_btn = self.wait_for_any_template(
            templates=[
                "legend_trials/challenge_ch.png",
                "legend_trials/challenge_ge.png",
            ],
            threshold=0.8,
            grayscale=True,
            crop_left=0.3,
            crop_right=0.3,
            crop_top=0.2,
            crop_bottom=0.2,
            delay=0.5,
            timeout=self.MIN_TIMEOUT,
        )
        _, x, y = challenge_btn
        self.click(x, y)
        return None

    def __navigate_to_legend_trials_select_tower(self) -> None:
        def check_for_legend_trials_s_header() -> bool:
            header = self.find_template_match(
                template="legend_trials/s_header.png",
                crop_right=0.8,
                crop_bottom=0.8,
            )
            return header is not None

        self._navigate_to_default_state(check_callable=check_for_legend_trials_s_header)

        logging.info("Navigating to Legend Trials tower selection")
        s_header = self.find_template_match(
            template="legend_trials/s_header.png",
            crop_right=0.8,
            crop_bottom=0.8,
            use_previous_screenshot=True,
        )
        if not s_header:
            logging.info("Clicking Battle Modes button")
            self.click(460, 1830, scale=True)
            label = self.wait_for_template(
                template="legend_trials/label.png",
                timeout_message="Could not find Legend Trial Label",
            )
            self.click(*label)
            self.wait_for_template(
                template="legend_trials/s_header.png",
                crop_right=0.8,
                crop_bottom=0.8,
                timeout_message="Could not find Season Legend Trial Header",
            )
        sleep(1)
        return None
