"""Tests for the Homestead craft stop-condition logic."""

from unittest.mock import MagicMock, patch

import numpy as np
from adb_auto_player.exceptions import GameTimeoutError
from adb_auto_player.games.afk_journey.mixins.homestead_helper import (
    HomesteadHelperMixin,
    _RequestFulfillment,
)
from adb_auto_player.games.afk_journey.settings import HomesteadCraftStopCondition


class _Stub(HomesteadHelperMixin):
    """Minimal stub - only pure-logic methods exercised."""

    def __init__(self) -> None:
        self._settings = MagicMock()
        self._device = MagicMock()

    @property
    def settings(self):
        return self._settings

    @property
    def device(self):
        return self._device

    def get_screenshot(self):
        return np.zeros((10, 10, 3), dtype=np.uint8)


class TestReadHomesteadStamina:
    def test_confirms_value_once_two_reads_agree(self):
        bot = _Stub()
        bot._homestead_stamina_ocr_backend = MagicMock(
            extract_text=lambda _: "4800/5000"
        )

        assert bot._read_homestead_stamina() == 4800

    def test_returns_none_when_unreadable(self):
        bot = _Stub()
        bot._homestead_stamina_ocr_backend = MagicMock(extract_text=lambda _: "")

        with patch("adb_auto_player.games.afk_journey.mixins.homestead_helper.sleep"):
            assert bot._read_homestead_stamina() is None

    def test_retries_after_a_transient_blank_read(self):
        """Regression test: one blank OCR read must not give up immediately.

        Previously a single unreadable frame (e.g. the UI still settling
        right after navigating back to the homestead overview) made this
        return None outright, which the stop-condition check treats as
        "not reached" - silently letting a craft trip through that should
        have been blocked.
        """
        bot = _Stub()
        bot._homestead_stamina_ocr_backend = MagicMock(
            extract_text=MagicMock(side_effect=["", "4100/5000", "4100/5000"])
        )

        with patch("adb_auto_player.games.afk_journey.mixins.homestead_helper.sleep"):
            assert bot._read_homestead_stamina() == 4100

    def test_returns_none_after_exhausting_all_attempts(self):
        bot = _Stub()
        bot._homestead_stamina_ocr_backend = MagicMock(
            extract_text=MagicMock(return_value="")
        )

        with patch(
            "adb_auto_player.games.afk_journey.mixins.homestead_helper.sleep"
        ) as mock_sleep:
            assert bot._read_homestead_stamina() is None

        assert (
            bot._homestead_stamina_ocr_backend.extract_text.call_count
            == bot.HOMESTEAD_STAMINA_READ_ATTEMPTS
        )
        assert mock_sleep.call_count == bot.HOMESTEAD_STAMINA_READ_ATTEMPTS - 1

    def test_a_single_misread_does_not_get_trusted(self):
        """Regression test: one plausible-but-wrong OCR read is not trusted.

        Previously any single successful regex match was returned
        immediately, so a garbled digit (a successful read, not an empty
        one - retrying-on-empty doesn't catch this) could report a Stamina
        value higher than reality, letting the stop-condition check think
        there was still margin for another craft batch when there wasn't.
        """
        bot = _Stub()
        bot._homestead_stamina_ocr_backend = MagicMock(
            extract_text=MagicMock(side_effect=["4300/5000", "4100/5000", "4100/5000"])
        )

        with patch("adb_auto_player.games.afk_journey.mixins.homestead_helper.sleep"):
            assert bot._read_homestead_stamina() == 4100

    def test_persistent_disagreement_returns_none(self):
        bot = _Stub()
        bot._homestead_stamina_ocr_backend = MagicMock(
            extract_text=MagicMock(
                side_effect=[
                    "4300/5000",
                    "4100/5000",
                    "4250/5000",
                    "4180/5000",
                    "4090/5000",
                ]
            )
        )

        with patch("adb_auto_player.games.afk_journey.mixins.homestead_helper.sleep"):
            assert bot._read_homestead_stamina() is None

    def test_uses_the_higher_accuracy_engine_by_default(self):
        bot = _Stub()

        with patch(
            "adb_auto_player.games.afk_journey.mixins.homestead_helper.RapidOCRBackend"
        ) as mock_backend_cls:
            mock_backend_cls.pp_ocr_v5_rec.return_value = MagicMock(
                extract_text=lambda _: "4800/5000"
            )
            assert bot._read_homestead_stamina() == 4800

        mock_backend_cls.pp_ocr_v5_rec.assert_called_once()


class TestHomesteadCraftStopConditionReached:
    def test_item_count_mode_stops_at_limit(self):
        bot = _Stub()
        bot.settings.homestead.craft_stop_condition = (
            HomesteadCraftStopCondition.ITEM_COUNT
        )
        bot.settings.homestead.craft_item_limit = 80
        bot._homestead_crafted_count = 80

        assert bot._homestead_craft_stop_condition_reached() is True

    def test_item_count_mode_continues_below_limit(self):
        bot = _Stub()
        bot.settings.homestead.craft_stop_condition = (
            HomesteadCraftStopCondition.ITEM_COUNT
        )
        bot.settings.homestead.craft_item_limit = 80
        bot._homestead_crafted_count = 70

        assert bot._homestead_craft_stop_condition_reached() is False

    def test_stamina_mode_stops_when_next_batch_would_undershoot_target(self):
        bot = _Stub()
        bot.settings.homestead.craft_stop_condition = (
            HomesteadCraftStopCondition.STAMINA_CONSUMED
        )
        bot.settings.homestead.craft_stamina_target = 4000

        # 4090 - 100 (fixed batch cost) = 3990, below the 4000 target.
        with patch.object(bot, "_read_homestead_stamina", return_value=4090):
            assert bot._homestead_craft_stop_condition_reached() is True

        with patch.object(bot, "_read_homestead_stamina", return_value=3500):
            assert bot._homestead_craft_stop_condition_reached() is True

    def test_stamina_mode_continues_when_next_batch_stays_at_or_above_target(self):
        bot = _Stub()
        bot.settings.homestead.craft_stop_condition = (
            HomesteadCraftStopCondition.STAMINA_CONSUMED
        )
        bot.settings.homestead.craft_stamina_target = 4000

        # 4101 - 100 = 4001, still above the target.
        with patch.object(bot, "_read_homestead_stamina", return_value=4101):
            assert bot._homestead_craft_stop_condition_reached() is False

        # 4100 - 100 = 4000, landing exactly on the target is fine.
        with patch.object(bot, "_read_homestead_stamina", return_value=4100):
            assert bot._homestead_craft_stop_condition_reached() is False

    def test_stamina_mode_unreadable_does_not_stop(self):
        bot = _Stub()
        bot.settings.homestead.craft_stop_condition = (
            HomesteadCraftStopCondition.STAMINA_CONSUMED
        )
        bot.settings.homestead.craft_stamina_target = 4000

        with patch.object(bot, "_read_homestead_stamina", return_value=None):
            assert bot._homestead_craft_stop_condition_reached() is False


class TestHandleInsufficientResourcesPopup:
    def test_no_navigation_link_dismisses_and_returns_false(self):
        bot = _Stub()

        with (
            patch.object(bot, "game_find_template_match", return_value=None),
            patch.object(bot, "tap") as mock_tap,
            patch("adb_auto_player.games.afk_journey.mixins.homestead_helper.sleep"),
        ):
            result = bot._handle_insufficient_resources_popup()

        assert result is False
        mock_tap.assert_called_once_with(
            bot.HOMESTEAD_INSUFFICIENT_RESOURCES_CLOSE_POINT
        )

    def test_navigation_link_taps_arrow_and_delegates_to_ingredient_batch(self):
        bot = _Stub()
        arrow_match = MagicMock()

        with (
            patch.object(bot, "game_find_template_match", return_value=arrow_match),
            patch.object(bot, "tap") as mock_tap,
            patch.object(
                bot, "_craft_ingredient_batch", return_value=True
            ) as mock_craft,
        ):
            result = bot._handle_insufficient_resources_popup()

        assert result is True
        mock_tap.assert_called_once_with(arrow_match)
        mock_craft.assert_called_once()


class TestHandleCraftingToMax:
    def test_insufficient_resources_before_action_tap_delegates_and_returns_result(
        self,
    ):
        bot = _Stub()
        blocked_result = MagicMock(
            template=bot.HOMESTEAD_INSUFFICIENT_RESOURCES_TEMPLATE
        )

        with (
            patch.object(bot, "wait_for_any_template", return_value=blocked_result),
            patch.object(bot, "tap"),
            patch.object(
                bot, "_handle_insufficient_resources_popup", return_value=True
            ) as mock_handle,
            patch("adb_auto_player.games.afk_journey.mixins.homestead_helper.sleep"),
        ):
            assert bot._handle_crafting_to_max() is True

        mock_handle.assert_called_once()
        assert getattr(bot, "_homestead_crafted_count", 0) == 0

    def test_insufficient_resources_after_action_tap_delegates_and_returns_result(
        self,
    ):
        bot = _Stub()
        ready_result = MagicMock(template=bot.HOMESTEAD_ACTION_BUTTON_TEMPLATES[0])
        blocked_result = MagicMock(
            template=bot.HOMESTEAD_INSUFFICIENT_RESOURCES_TEMPLATE
        )

        with (
            patch.object(
                bot,
                "wait_for_any_template",
                side_effect=[ready_result, blocked_result],
            ),
            patch.object(bot, "tap"),
            patch.object(
                bot, "_handle_insufficient_resources_popup", return_value=False
            ) as mock_handle,
            patch("adb_auto_player.games.afk_journey.mixins.homestead_helper.sleep"),
        ):
            assert bot._handle_crafting_to_max() is False

        mock_handle.assert_called_once()
        assert getattr(bot, "_homestead_crafted_count", 0) == 0

    def test_successful_craft_returns_true_and_increments_count(self):
        bot = _Stub()
        ready_result = MagicMock(template=bot.HOMESTEAD_ACTION_BUTTON_TEMPLATES[0])

        with (
            patch.object(
                bot, "wait_for_any_template", side_effect=[ready_result, ready_result]
            ),
            patch.object(bot, "tap"),
            patch("adb_auto_player.games.afk_journey.mixins.homestead_helper.sleep"),
        ):
            assert bot._handle_crafting_to_max() is True

        assert bot._homestead_crafted_count == bot.HOMESTEAD_CRAFT_BATCH_SIZE

    def test_grey_button_after_craft_runs_ingredient_craft_when_stop_not_reached(self):
        """A second craft batch is only spent while still under the target."""
        bot = _Stub()
        ready_result = MagicMock(template=bot.HOMESTEAD_ACTION_BUTTON_TEMPLATES[0])
        grey_result = MagicMock(template=bot.HOMESTEAD_GRAY_ACTION_BUTTON_TEMPLATES[0])

        with (
            patch.object(
                bot, "wait_for_any_template", side_effect=[ready_result, grey_result]
            ),
            patch.object(bot, "tap"),
            patch.object(
                bot, "_homestead_craft_stop_condition_reached", return_value=False
            ),
            patch.object(
                bot, "_handle_missing_ingredient_craft"
            ) as mock_ingredient_craft,
            patch("adb_auto_player.games.afk_journey.mixins.homestead_helper.sleep"),
        ):
            assert bot._handle_crafting_to_max() is True

        mock_ingredient_craft.assert_called_once()

    def test_grey_button_after_craft_skips_ingredient_craft_when_stop_reached(self):
        """Regression test: a trip must not spend a second, unbudgeted batch.

        Previously, if the action button came back grey after a successful
        craft (a required ingredient ran out), the bot would immediately
        craft that ingredient too - a second Stamina-consuming batch within
        the same trip that the pre-trip stop-condition check never budgeted
        for. That let a single trip overshoot a Stamina target that was
        already within one batch's reach (e.g. target 4100, starting at
        4200: the pre-trip check only ruled out going below 4100 with *one*
        batch, but two batches landed at 4000).
        """
        bot = _Stub()
        ready_result = MagicMock(template=bot.HOMESTEAD_ACTION_BUTTON_TEMPLATES[0])
        grey_result = MagicMock(template=bot.HOMESTEAD_GRAY_ACTION_BUTTON_TEMPLATES[0])

        with (
            patch.object(
                bot, "wait_for_any_template", side_effect=[ready_result, grey_result]
            ),
            patch.object(bot, "tap"),
            patch.object(
                bot, "_homestead_craft_stop_condition_reached", return_value=True
            ),
            patch.object(
                bot, "_handle_missing_ingredient_craft"
            ) as mock_ingredient_craft,
            patch("adb_auto_player.games.afk_journey.mixins.homestead_helper.sleep"),
        ):
            assert bot._handle_crafting_to_max() is True

        mock_ingredient_craft.assert_not_called()
        assert bot._homestead_crafted_count == bot.HOMESTEAD_CRAFT_BATCH_SIZE


class TestCraftIngredientBatch:
    def test_successful_batch_returns_true(self):
        bot = _Stub()

        with (
            patch.object(bot, "wait_for_any_template"),
            patch.object(bot, "wait_for_template"),
            patch.object(bot, "tap"),
            patch.object(bot, "press_back_button") as mock_back,
            patch("adb_auto_player.games.afk_journey.mixins.homestead_helper.sleep"),
        ):
            assert bot._craft_ingredient_batch() is True

        bot.device.swipe.assert_called_once()
        mock_back.assert_called_once()

    def test_screen_never_loads_returns_false(self):
        bot = _Stub()

        with (
            patch.object(
                bot, "wait_for_any_template", side_effect=GameTimeoutError("x")
            ),
            patch.object(bot, "press_back_button") as mock_back,
            patch("adb_auto_player.games.afk_journey.mixins.homestead_helper.sleep"),
        ):
            assert bot._craft_ingredient_batch() is False

        mock_back.assert_called_once()

    def test_craft_never_completes_returns_false(self):
        bot = _Stub()

        with (
            patch.object(bot, "wait_for_any_template"),
            patch.object(bot, "wait_for_template", side_effect=GameTimeoutError("x")),
            patch.object(bot, "tap"),
            patch.object(bot, "press_back_button") as mock_back,
            patch("adb_auto_player.games.afk_journey.mixins.homestead_helper.sleep"),
        ):
            assert bot._craft_ingredient_batch() is False

        mock_back.assert_called_once()


class TestFulfillRequestsBestFirstBlocked:
    def test_blocked_increments_counter_and_returns_true(self):
        bot = _Stub()
        bot._homestead_blocked_craft_count = 0

        with (
            patch.object(bot, "_select_best_request", return_value=0),
            patch.object(
                bot,
                "_fulfill_selected_request",
                return_value=_RequestFulfillment.BLOCKED,
            ),
        ):
            assert bot._fulfill_requests_best_first() is True

        assert bot._homestead_blocked_craft_count == 1


class TestHandleHomesteadRequestsStopCondition:
    def test_stop_condition_already_met_skips_the_first_craft_attempt(self):
        """Regression test: the guard must run before the first craft trip.

        Previously the stop condition was only checked *after* a craft trip,
        so a trip that was already at/past the target when the mode started
        would go through unguarded and overshoot it.
        """
        bot = _Stub()

        with (
            patch.object(
                bot, "_homestead_craft_stop_condition_reached", return_value=True
            ),
            patch.object(bot, "game_find_template_match") as mock_find,
            patch.object(bot, "tap") as mock_tap,
            patch.object(bot, "_fulfill_requests_best_first") as mock_fulfill,
            patch("adb_auto_player.games.afk_journey.mixins.homestead_helper.sleep"),
        ):
            bot._handle_homestead_requests()

        mock_find.assert_not_called()
        mock_tap.assert_not_called()
        mock_fulfill.assert_not_called()
