"""AFK Journey Base Module."""

import logging
import re
from time import sleep
from typing import Any

from adb_auto_player import (
    Game,
    TemplateMatchParams,
)
from adb_auto_player.decorators import register_game
from adb_auto_player.exceptions import (
    AutoPlayerWarningError,
    GameActionFailedError,
    GameTimeoutError,
)
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.decorators import GameGUIMetadata
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.util import SummaryGenerator

from .afkjourneynavigation import AFKJourneyNavigation
from .battle_state import BattleState, Mode
from .config import Config
from .gui_category import AFKJCategory
from .popup_handler import AFKJourneyPopupHandler


@register_game(
    name="AFK Journey",
    config_file_path="afk_journey/AFKJourney.toml",
    gui_metadata=GameGUIMetadata(
        config_class=Config,
        categories=list(AFKJCategory),
    ),
)
class AFKJourneyBase(AFKJourneyNavigation, AFKJourneyPopupHandler, Game):
    """AFK Journey Base Class."""

    def __init__(self) -> None:
        """Initialize AFKJourneyBase."""
        super().__init__()
        self.supports_portrait = True
        self.package_name_substrings = [
            "com.farlightgames.igame.gp",
        ]

        # to allow passing properties over multiple functions
        self.battle_state: BattleState = BattleState()

    # Timeout constants (in seconds)
    BATTLE_TIMEOUT: int = 240
    MIN_TIMEOUT: int = 10
    FAST_TIMEOUT: int = 3

    # Error strings
    LANG_ERROR: str = "Is the game language set to English?"
    BATTLE_TIMEOUT_ERROR_MESSAGE: str = (
        "Battle over screen not found after 4 minutes, the game may be slow or stuck."
    )

    def start_up(self, device_streaming: bool = True) -> None:
        """Give the bot eyes."""
        if self.device is None:
            self.open_eyes(device_streaming=device_streaming)

    def _load_config(self) -> Config:
        """Load config TOML."""
        self.config = Config.from_toml(self._get_config_file_path())
        return self.config

    def get_config(self) -> Config:
        """Get config."""
        if self.config is None:
            return self._load_config()
        return self.config

    def _get_config_attribute_from_mode(self, attribute: str) -> Any:
        """Retrieve a configuration attribute based on the current game mode.

        Args:
            attribute (str): The name of the configuration attribute to retrieve.

        Returns:
            The value of the specified attribute from the configuration corresponding
            to the current game mode.
        """
        match self.battle_state.mode:
            case Mode.DURAS_TRIALS | Mode.DURAS_NIGHTMARE_TRIALS:
                return getattr(self.get_config().duras_trials, attribute)
            case Mode.LEGEND_TRIALS:
                return getattr(self.get_config().legend_trials, attribute)
            case _:
                return getattr(self.get_config().afk_stages, attribute)

    def _handle_battle_screen(
        self, use_suggested_formations: bool = True, skip_manual: bool = False
    ) -> bool:
        """Handles logic for battle screen.

        Args:
            use_suggested_formations: if True copy formations from Records
            skip_manual: Skip formations labeled as manual clear.

        Returns:
            True if the battle was won, False otherwise.
        """
        formations = self._get_config_attribute_from_mode("formations")

        self.battle_state.formation_num = 0
        if not use_suggested_formations:
            formations = 1

        if (
            self._get_config_attribute_from_mode(
                "use_current_formation_before_suggested_formation"
            )
            and self._handle_single_stage()
        ):
            logging.info("Battle using current Formation.")
            return True

        while self.battle_state.formation_num < formations:
            self.battle_state.formation_num += 1

            if (
                use_suggested_formations
                and not self._copy_suggested_formation_from_records(
                    formations, skip_manual
                )
            ):
                continue
            else:
                _ = self.wait_for_any_template(
                    templates=[
                        "battle/records.png",
                        "battle/formations_icon.png",
                    ],
                    crop_regions=CropRegions(top=0.5),
                )

            if self._handle_single_stage():
                return True

            if self.battle_state.max_attempts_reached:
                self.battle_state.max_attempts_reached = False
                return False

        if formations > 1:
            logging.info("Stopping Battle, tried all attempts for all Formations")
        return False

    def _copy_suggested_formation(
        self, formations: int = 1, start_count: int = 1
    ) -> bool:
        """Helper to copy suggested formations from records.

        Args:
            formations (int): Number of formation to copy
            start_count (int): First formation to copy

        Returns:
            True if successful, False otherwise
        """
        if formations < self.battle_state.formation_num:
            return False

        logging.info(f"Copying Formation #{self.battle_state.formation_num}")
        counter = self.battle_state.formation_num - start_count
        while counter > 0:
            formation_next = self.wait_for_template(
                "battle/formation_next.png",
                crop_regions=CropRegions(left=0.8, top=0.5, bottom=0.4),
                timeout=self.MIN_TIMEOUT,
                timeout_message=(
                    f"Formation #{self.battle_state.formation_num} not found"
                ),
            )
            start_image = self.get_screenshot()
            self.tap(formation_next)
            self.wait_for_roi_change(
                start_image=start_image,
                crop_regions=CropRegions(left=0.2, right=0.2, top=0.15, bottom=0.8),
                threshold=ConfidenceValue("80%"),
                timeout=self.MIN_TIMEOUT,
                timeout_message=(
                    f"Formation #{self.battle_state.formation_num} not found"
                ),
            )
            counter -= 1
        excluded_hero: str | None = self._formation_contains_excluded_hero()
        if excluded_hero is not None:
            logging.warning(
                f"Formation contains excluded Hero: '{excluded_hero}' skipping"
            )
            start_count = self.battle_state.formation_num
            self.battle_state.formation_num += 1
            return self._copy_suggested_formation(formations, start_count)
        return True

    def _copy_suggested_formation_from_records(
        self, formations: int = 1, skip_manual: bool = False
    ) -> bool:
        """Copy suggested formations from records.

        Returns:
            True if successful, False otherwise.
        """
        _ = self.wait_for_template(
            template="battle/records.png",
            crop_regions=CropRegions(right=0.5, top=0.8),
        )
        self._tap_till_template_disappears(
            template="battle/records.png",
            crop_regions=CropRegions(right=0.5, top=0.8),
            delay=10.0,
            error_message="No videos available for this battle",
        )

        try:
            _ = self.wait_for_template(
                "battle/copy.png",
                crop_regions=CropRegions(left=0.3, right=0.1, top=0.7, bottom=0.1),
                timeout=self.MIN_TIMEOUT,
            )
        except GameTimeoutError:
            raise AutoPlayerWarningError("No more formations available for this battle")

        start_count = 1

        while True:
            if not self._copy_suggested_formation(formations, start_count):
                return False
            sleep(2)
            if skip_manual:
                manual_clear = self.find_any_template(
                    templates=[
                        "battle/manual_battle.png",
                        # decided to keep old one just in case
                        "battle/manual_battle_old1.png",
                    ],
                    crop_regions=CropRegions(
                        top=0.5,
                        right=0.5,
                    ),
                    threshold=ConfidenceValue("80%"),
                )
                if manual_clear:
                    logging.info("Manual formation found, skipping.")
                    start_count = self.battle_state.formation_num
                    self.battle_state.formation_num += 1
                    continue
            self._tap_till_template_disappears(
                template="battle/copy.png",
                crop_regions=CropRegions(left=0.3, right=0.1, top=0.7, bottom=0.1),
            )
            sleep(1)
            cancel = self.game_find_template_match(
                template="cancel.png",
                crop_regions=CropRegions(left=0.1, right=0.5, top=0.6, bottom=0.3),
            )
            if cancel:
                logging.warning(
                    "Formation contains locked Artifacts or Heroes skipping"
                )
                self.tap(cancel)
                start_count = self.battle_state.formation_num
                self.battle_state.formation_num += 1
            else:
                self._click_confirm_on_popup()
                logging.debug("Formation copied")
                return True
        return False

    def _formation_contains_excluded_hero(self) -> str | None:
        """Skip formations with excluded heroes.

        Returns:
            str | None: Name of excluded hero
        """
        excluded_heroes_dict: dict[str, str] = {
            f"heroes/{re.sub(r'[\s&]', '', name.value.lower())}.png": name.value
            for name in self.get_config().general.excluded_heroes
        }

        if not excluded_heroes_dict:
            return None

        filtered_dict = {}

        for key, value in excluded_heroes_dict.items():
            filtered_dict[key] = value

        return self._find_any_excluded_hero(filtered_dict)

    def _find_any_excluded_hero(self, excluded_heroes: dict[str, str]) -> str | None:
        """Find excluded hero templates.

        Args:
            excluded_heroes (dict[str, str]): Dictionary of excluded heroes.

        Returns:
            str | None: Name of excluded hero
        """
        sleep(0.5)
        try:
            result = self.wait_for_any_template(
                templates=list(excluded_heroes.keys()),
                crop_regions=CropRegions(left=0.1, right=0.2, top=0.3, bottom=0.4),
                timeout=1.0,
                delay=0.5,
            )
            return excluded_heroes.get(result.template)
        except GameTimeoutError:
            return None

    def _start_battle(self) -> bool:
        """Begin battle.

        Returns:
            bool: True if battle started, False otherwise.
        """
        spend_gold: str = self._get_config_attribute_from_mode("spend_gold")

        result = self.wait_for_any_template(
            templates=[
                "battle/records.png",
                "battle/formations_icon.png",
            ],
            crop_regions=CropRegions(top=0.5),
        )

        try:
            self._tap_coordinates_till_template_disappears(
                coordinates=Point(x=850, y=1780),
                scale=True,
                template_match_params=TemplateMatchParams(
                    template=result.template,
                ),
            )
        except GameActionFailedError:
            logging.warning("Failed to start Battle, are no Heroes selected?")
            return False
        sleep(1)

        # Need to double-check the order of prompts here
        if self.find_any_template(["battle/spend.png", "battle/gold.png"]):
            if not spend_gold:
                logging.warning("Not spending gold returning")
                self.battle_state.max_attempts_reached = True
                self.press_back_button()
                return False
            else:
                self._click_confirm_on_popup()

        # Just handle however many popups show up
        # Needs a counter to prevent infinite loop on freeze though
        max_count = 10
        count = 0
        while self._click_confirm_on_popup() and count < max_count:
            self._click_confirm_on_popup()
            count += 1
            sleep(0.5)
        return True

    def _click_confirm_on_popup(self) -> bool:
        """Confirm popups.

        Returns:
            bool: True if confirmed, False if not.
        """
        if self.handle_confirmation_popups():
            return True

        # Legacy code keeping it as a fallback
        result = self.find_any_template(
            templates=["navigation/confirm.png", "confirm_text.png"],
            crop_regions=CropRegions(top=0.4),
        )
        if result:
            self.tap(result)
            sleep(1)
            return True
        return False

    def _get_battle_over_templates(self) -> list[str]:
        match self.battle_state.mode:
            case Mode.AFK_STAGES | Mode.SEASON_TALENT_STAGES:
                return [
                    "next.png",
                    "battle/victory_rewards.png",
                    "retry.png",
                    "navigation/confirm.png",
                    "battle/power_up.png",
                    "battle/result.png",
                    "afk_stages/tap_to_close.png",
                ]

            case Mode.DURAS_TRIALS | Mode.DURAS_NIGHTMARE_TRIALS:
                return [
                    "duras_trials/no_next.png",
                    "duras_trials/first_clear.png",
                    "duras_trials/end_sunrise.png",
                    "next.png",
                    "battle/victory_rewards.png",
                    "retry.png",
                    "navigation/confirm.png",
                    "battle/power_up.png",
                    "battle/result.png",
                ]

            case Mode.LEGEND_TRIALS:
                return [
                    "legend_trials/available_after.png",
                    "next.png",
                    "battle/victory_rewards.png",
                    "retry.png",
                    "navigation/confirm.png",
                    "battle/power_up.png",
                    "battle/result.png",
                ]
            case _:
                return [
                    "next.png",
                    "battle/victory_rewards.png",
                    "retry.png",
                    "navigation/confirm.png",
                    "battle/power_up.png",
                    "battle/result.png",
                ]

    def _handle_single_stage(self) -> bool:
        """Handles a single stage of a battle.

        Returns:
            bool: True if the battle was successful, False if not.
        """
        logging.debug("_handle_single_stage")
        attempts = self._get_config_attribute_from_mode("attempts")
        count = 0
        result: bool | None = None
        battle_over_templates = self._get_battle_over_templates()

        while count < attempts:
            count += 1
            logging.info(f"Starting Battle #{count}")
            if not self._start_battle():
                result = False
                break

            if self.battle_state.section_header:
                SummaryGenerator.increment(self.battle_state.section_header, "Battles")

            match = self.wait_for_any_template(
                templates=battle_over_templates,
                timeout=self.BATTLE_TIMEOUT,
                crop_regions=CropRegions(top=0.4),
                delay=1.0,
                timeout_message=self.BATTLE_TIMEOUT_ERROR_MESSAGE,
            )

            match match.template:
                case "duras_trials/no_next.png":
                    self.press_back_button()
                    result = True
                    break

                case "battle/victory_rewards.png":
                    self.tap(Point(x=550, y=1800), scale=True)
                    result = True
                    break

                case "battle/power_up.png":
                    self.tap(Point(x=550, y=1800), scale=True)
                    result = False
                    break

                case "navigation/confirm.png":
                    logging.error(
                        "Network Error or Battle data differs between client and server"
                    )
                    self.tap(match)
                    sleep(3)
                    result = False
                    break

                case (
                    "next.png"
                    | "duras_trials/first_clear.png"
                    | "duras_trials/end_sunrise.png"
                ):
                    result = True
                    break

                case "retry.png":
                    logging.info(f"Lost Battle #{count}")
                    self.tap(match)
                    # Do not break so the loop continues

                case "battle/result.png":
                    self.tap(Point(x=950, y=1800), scale=True)
                    result = True
                    break

                case (
                    "afk_stages/tap_to_close.png" | "legend_trials/available_after.png"
                ):
                    raise AutoPlayerWarningError("Final Stage reached, exiting...")

        # If no branch set result, default to False.
        if result is None:
            result = False

        return result

    def _handle_guide_popup(
        self,
    ) -> None:
        """Close out of guide popups."""
        while True:
            result = self.find_any_template(
                templates=["guide/close.png", "guide/next.png"],
                crop_regions=CropRegions(top=0.4),
            )
            if result is None:
                break
            self.tap(result)
            sleep(1)
