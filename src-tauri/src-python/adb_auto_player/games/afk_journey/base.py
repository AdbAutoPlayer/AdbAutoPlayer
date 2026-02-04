"""AFK Journey Base Module."""

import logging
import re
from datetime import datetime, timedelta
from time import sleep
from typing import Any

from adb_auto_player.decorators import register_cache, register_game
from adb_auto_player.exceptions import (
    AutoPlayerWarningError,
    GameActionFailedError,
    GameNotRunningOrFrozenError,
    GameTimeoutError,
)
from adb_auto_player.game import Game
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.decorators import CacheGroup, GameGUIMetadata
from adb_auto_player.models.device import Resolution
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.models.template_matching import TemplateMatchResult
from adb_auto_player.tauri_context import profile_aware_cache
from adb_auto_player.util import SummaryGenerator

from ...image_manipulation import Cropping
from ...template_matching import TemplateMatcher
from .battle_state import BattleState, Mode
from .gui_category import AFKJCategory
from .navigation import Navigation
from .settings import Settings


@register_game(
    name="AFK Journey",
    settings_file="AFKJourney.toml",
    gui_metadata=GameGUIMetadata(
        settings_class=Settings,
        categories=list(AFKJCategory),
    ),
)
class AFKJourneyBase(Navigation, Game):
    """AFK Journey Base Class."""

    def __init__(self) -> None:
        """Initialize AFKJourneyBase."""
        super().__init__()
        self.base_resolution: Resolution = Resolution.from_string("1080x1920")
        self.package_name_prefixes = [
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
        self.open_eyes(device_streaming=device_streaming)

    @property
    @register_cache(CacheGroup.GAME_SETTINGS)
    @profile_aware_cache(maxsize=1)
    def settings(self) -> Settings:
        """Get Settings."""
        return Settings.from_toml(self.settings_file_path)

    def _get_settings_for_mode(self, attribute: str) -> Any:
        """Retrieve Settings based on the current game mode.

        Args:
            attribute (str): The name of the Settings attribute to retrieve.

        Returns:
            The value of the specified attribute from the Settings corresponding
            to the current game mode.
        """
        match self.battle_state.mode:
            case Mode.DURAS_TRIALS:
                return getattr(self.settings.duras_trials, attribute)
            case Mode.LEGEND_TRIALS:
                return getattr(self.settings.legend_trials, attribute)
            case _:
                return getattr(self.settings.afk_stages, attribute)

    def _re_enter_battle_for_duras(self):
        try:
            _ = self.wait_for_template(
                "duras_trials/socketed_charms_overview",
                timeout=self.FAST_TIMEOUT,
            )
            self._tap_till_template_disappears("duras_trials/battle")
        except GameTimeoutError:
            pass

    def _handle_battle_screen(
        self,
        use_suggested_formations: bool = True,
    ) -> bool:
        """Handles logic for battle screen.

        Args:
            use_suggested_formations: if True copy formations from Records

        Returns:
            True if the battle was won, False otherwise.
        """
        skip_manual_formations = self._get_settings_for_mode("skip_manual_formations")
        run_manual_last = self._get_settings_for_mode("run_manual_formations_last")

        # Handle two-pass battle
        if run_manual_last and use_suggested_formations and not skip_manual_formations:
            return self._handle_two_pass_battle(
                use_suggested_formations=use_suggested_formations
            )

        # Handle skipping all manual or running all formations
        return self._handle_battle_screen_pass(
            use_suggested_formations=use_suggested_formations,
            skip_manual=skip_manual_formations,
        )

    def _handle_two_pass_battle(self, use_suggested_formations: bool) -> bool:
        """Handle two-pass battle: first non-manual, then manual.

        Args:
            use_suggested_formations: if True copy formations from Records

        Returns:
            True if the battle was won, False otherwise.
        """
        passes = (
            ("First", "trying all non-manual formations first.", {"skip_manual": True}),
            ("Second", "trying manual formations only.", {"only_manual": True}),
        )

        for label, log, kwargs in passes:
            logging.info(f"{label} pass: {log}")

            if kwargs.get("only_manual"):
                self._ensure_on_battle_screen()
                self.battle_state.formation_num = 0  # Reset counter for second pass

            if self._handle_battle_screen_pass(
                use_suggested_formations=use_suggested_formations,
                **kwargs,
            ):
                return True

        return False

    def _ensure_on_battle_screen(self) -> None:
        """Ensure we're on the battle screen, navigating if necessary."""
        retry_button = self._find_retry_button(timeout=5.0)
        if retry_button:
            self.tap(retry_button)
            sleep(2)
            return

        if self._find_battle_screen(timeout=2.0):
            return

        self.press_back_button()
        sleep(2)
        self._find_battle_screen(timeout=10.0, raise_on_timeout=True)

    def _find_retry_button(self, timeout: float) -> TemplateMatchResult | None:
        """Locate the retry button if present."""
        try:
            return self.wait_for_any_template(
                templates=["retry.png"],
                timeout=timeout,
                crop_regions=CropRegions(top=0.4),
            )
        except GameTimeoutError:
            return None

    def _find_battle_screen(
        self, timeout: float, *, raise_on_timeout: bool = False
    ) -> TemplateMatchResult | None:
        """Locate the battle screen records button."""
        try:
            return self.wait_for_template(
                template="battle/records.png",
                crop_regions=CropRegions(right=0.5, top=0.8),
                timeout=timeout,
            )
        except GameTimeoutError as error:
            if raise_on_timeout:
                raise error
            return None

    def _handle_battle_screen_pass(
        self,
        use_suggested_formations: bool = True,
        skip_manual: bool = False,
        only_manual: bool = False,
    ) -> bool:
        """Handles a single pass through formations.

        Args:
            use_suggested_formations: if True copy formations from Records
            skip_manual: Skip formations labeled as manual clear.
            only_manual: Only try manual formations (skip non-manual).

        Returns:
            True if the battle was won, False otherwise.
        """
        formations = self._get_settings_for_mode("formations")
        self.battle_state.formation_num = 0
        if not use_suggested_formations:
            formations = 1

        run_current_first = (
            self._get_settings_for_mode(
                "use_current_formation_before_suggested_formation"
            )
            and not only_manual
        )

        if run_current_first:
            logging.info("Battle using current Formation.")
            if self._handle_single_stage():
                return True

        while self.battle_state.formation_num < formations:
            self.battle_state.formation_num += 1

            if self.battle_state.mode == Mode.DURAS_TRIALS:
                self._re_enter_battle_for_duras()

            if use_suggested_formations:
                try:
                    copied = self._copy_suggested_formation(
                        formations, skip_manual, only_manual
                    )
                except AutoPlayerWarningError:
                    logging.info("No more formations available, ending this pass.")
                    break

                if not copied:
                    continue

            if self._handle_single_stage():
                return True

            if self.battle_state.max_attempts_reached:
                self.battle_state.max_attempts_reached = False
                return False

        if formations > 1:
            logging.info("Stopping Battle, tried all attempts for all Formations")
        return False

    def _copy_suggested_formation(
        self,
        formations: int = 1,
        skip_manual: bool = False,
        only_manual: bool = False,
    ) -> bool:
        """Copy suggested formations from records.

        Args:
            formations: Number of formations to try
            skip_manual: Skip formations labeled as manual clear.
            only_manual: Only try manual formations (skip non-manual).

        Returns:
            True if successful, False otherwise.
        """
        self._navigate_to_formation_selection()

        start_count = 1

        while True:
            if formations < self.battle_state.formation_num:
                return False

            logging.info(f"Copying Formation #{self.battle_state.formation_num}")

            start_count = self._step_to_target_formation(start_count)

            if self._skip_formation(skip_manual, only_manual):
                self.battle_state.formation_num += 1
                continue

            if self._apply_current_formation():
                return True

            self.battle_state.formation_num += 1
        # Makes no sense but pre-commit can complain about potential None return
        return False

    def _step_to_target_formation(self, displayed_index: int) -> int:
        """Step through the records list until the target index is visible."""
        steps_needed = self.battle_state.formation_num - displayed_index

        if steps_needed <= 0:
            return displayed_index

        try:
            while steps_needed > 0:
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
                sleep(15.0 / 30.0)
                self.wait_for_roi_change(
                    start_image=start_image,
                    crop_regions=CropRegions(left=0.2, right=0.2, top=0.15, bottom=0.8),
                    threshold=ConfidenceValue("80%"),
                    timeout=self.MIN_TIMEOUT,
                    timeout_message=(
                        f"Formation #{self.battle_state.formation_num} not found"
                    ),
                )
                steps_needed -= 1
        except GameTimeoutError as error:
            raise AutoPlayerWarningError(error)

        return self.battle_state.formation_num

    def _apply_current_formation(self) -> bool:
        """Copy the currently selected formation and apply it."""
        self._tap_till_template_disappears(
            template="battle/copy.png",
            crop_regions=CropRegions(left=0.3, right=0.1, top=0.7, bottom=0.1),
            threshold=ConfidenceValue("75%"),
            sleep_duration=1.5,
        )

        cancel = self.game_find_template_match(
            template="cancel.png",
            crop_regions=CropRegions(left=0.1, right=0.5, top=0.6, bottom=0.3),
        )
        if cancel:
            logging.warning("Formation contains locked Artifacts or Heroes skipping")
            self.tap(cancel)
            return False

        self._click_confirm_on_popup()
        return True

    def _navigate_to_formation_selection(self) -> None:
        """Navigate to the formation selection screen."""
        self.wait_for_template(
            template="battle/records.png",
            crop_regions=CropRegions(right=0.5, top=0.8),
        )
        sleep(0.5)
        try:
            self._tap_till_template_disappears(
                template="battle/records.png",
                crop_regions=CropRegions(right=0.5, top=0.8),
                tap_delay=5.0,
                error_message="No videos available for this battle",
            )
            self.wait_for_template(
                "battle/copy.png",
                crop_regions=CropRegions(left=0.3, right=0.1, top=0.7, bottom=0.1),
                timeout=self.MIN_TIMEOUT,
                timeout_message="No more formations available for this battle",
            )
        except (GameTimeoutError, GameActionFailedError) as e:
            raise AutoPlayerWarningError(e)

        # UI is not interactable for some time fuck Lilith
        sleep(2)

    def _skip_formation(self, skip_manual: bool, only_manual: bool) -> bool:
        """Check if current formation should be skipped.

        Returns:
            True if formation should be skipped, False otherwise.
        """
        is_manual = self._is_manual_formation()

        # In only_manual mode, skip non-manual formations
        if only_manual and not is_manual:
            logging.info("Non-manual formation found, skipping (only trying manual).")
            return True

        if skip_manual and is_manual:
            logging.info("Manual formation found, skipping.")
            return True

        excluded_hero: str | None = self._formation_contains_excluded_hero()
        if excluded_hero is not None:
            logging.info(
                f"Formation contains excluded Hero: '{excluded_hero}', skipping."
            )
            return True

        return False

    def _formation_contains_excluded_hero(self) -> str | None:
        """Skip formations with excluded heroes.

        Returns:
            str | None: Name of excluded hero
        """
        excluded_heroes_dict: dict[str, str] = {
            f"heroes/{re.sub(r'[\s&]', '', name.value.lower())}.png": name.value
            for name in self.settings.general.excluded_heroes
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
        try:
            result = self.wait_for_any_template(
                templates=list(excluded_heroes.keys()),
                crop_regions=CropRegions(
                    left="10%", right="30%", top="35%", bottom="40%"
                ),
                threshold=ConfidenceValue("85%"),
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
        spend_gold: str = self._get_settings_for_mode("spend_gold")

        result = self.wait_for_any_template(
            templates=[
                "battle/records.png",
                "battle/formations_icon.png",
            ],
            crop_regions=CropRegions(top=0.5),
            timeout=10,
        )

        try:
            self._tap_coordinates_till_template_disappears(
                coordinates=Point(x=850, y=1780),
                template=result.template,
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
        if self.handle_popup_messages():
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
        # TODO possibly refactor this to have a map of template and actions
        # to perform when the template is encountered
        match self.battle_state.mode:
            case Mode.AFK_STAGES | Mode.SEASON_AFK_STAGES:
                return [
                    "next.png",
                    "battle/victory_rewards.png",
                    "retry.png",
                    "navigation/confirm.png",
                    "battle/power_up.png",
                    "battle/result.png",
                    "afk_stages/tap_to_close.png",
                ]

            case Mode.DURAS_TRIALS:
                return [
                    "duras_trials/no_next.png",
                    "duras_trials/first_clear_bottom_half.png",
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
        attempts = self._get_settings_for_mode("attempts")
        attempt = 0

        while attempt < attempts:
            attempt += 1
            logging.info(f"Starting Battle #{attempt}")
            if not self._start_battle():
                break

            if self.battle_state.section_header:
                SummaryGenerator.increment(self.battle_state.section_header, "Battles")

            result = self._is_battle_outcome_successful(attempt)
            if result is None:
                return False

            if result:
                return True

        return False

    def _wait_for_battle_over_template(
        self,
        freeze_check_interval: timedelta = timedelta(seconds=30),
    ) -> TemplateMatchResult:
        if self.battle_state.mode and self.battle_state.mode.has_timer():
            roi_crop = CropRegions(right="90%", bottom="90%")
            prev_crop = Cropping.crop(self.get_screenshot(), roi_crop)

            last_check = datetime.now()
            while True:
                screenshot = self.get_screenshot()
                match = self.find_any_template(
                    templates=self._get_battle_over_templates(),
                    crop_regions=CropRegions(top=0.4),
                    screenshot=screenshot,
                )
                if match is not None:
                    return match

                now = datetime.now()
                if now - last_check >= freeze_check_interval:
                    curr_crop = Cropping.crop(screenshot, roi_crop)
                    if TemplateMatcher.similar_image(
                        prev_crop.image,
                        curr_crop.image,
                        threshold=ConfidenceValue("98%"),
                    ):
                        raise GameNotRunningOrFrozenError("Battle frozen")
                    prev_crop = curr_crop
                    last_check = now
                sleep(1)

        return self.wait_for_any_template(
            templates=self._get_battle_over_templates(),
            timeout=self.BATTLE_TIMEOUT,
            crop_regions=CropRegions(top=0.4),
            delay=1.0,
            timeout_message=self.BATTLE_TIMEOUT_ERROR_MESSAGE,
        )

    def _is_battle_outcome_successful(
        self,
        attempt: int,
    ) -> bool | None:
        """Whether the battle was successful.

        None is for unclear scenarios, None cases should be replaced by Exceptions.
        """
        match = self._wait_for_battle_over_template()
        result = None
        match match.template:
            case "duras_trials/no_next.png":
                self.press_back_button()
                result = True

            case "battle/victory_rewards.png":
                self.tap(Point(x=550, y=1800))
                result = True

            case "battle/power_up.png":
                if self.battle_state.mode == Mode.DURAS_TRIALS:
                    self.tap(
                        Point(x=550, y=1800),
                        log_message=f"Lost Battle #{attempt}, retrying",
                    )
                    sleep(3)
                    self._re_enter_battle_for_duras()
                    result = False
                else:
                    # TODO should probably just throw an Exception
                    # I have no idea what this case is used for
                    # should leave comments in the future
                    self.tap(Point(x=550, y=1800))

            case "navigation/confirm.png":
                # TODO should probably just throw an Exception
                logging.error(
                    "Network Error or Battle data differs between client and server"
                )
                self.tap(match)
                sleep(3)

            case (
                "next.png"
                | "duras_trials/first_clear_bottom_half.png"
                | "duras_trials/end_sunrise.png"
            ):
                result = True

            case "retry.png":
                self.tap(match, log_message=f"Lost Battle #{attempt}, retrying")
                result = False

            case "battle/result.png":
                self.tap(Point(x=950, y=1800))
                result = True

            case "afk_stages/tap_to_close.png" | "legend_trials/available_after.png":
                raise AutoPlayerWarningError("Final Stage reached, exiting...")
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

    def _is_manual_formation(self) -> bool:
        """Check if current formation is manual.

        Returns:
            True if formation is manual, False otherwise.
        """
        try:
            _ = self.wait_for_any_template(
                templates=[
                    "battle/manual_battle.png",
                    "battle/manual_battle_old1.png",
                ],
                crop_regions=CropRegions(
                    top=0.5,
                    right=0.5,
                ),
                threshold=ConfidenceValue("80%"),
                delay=0.3,
                timeout=1.5,
            )
            return True
        except GameTimeoutError:
            return False
