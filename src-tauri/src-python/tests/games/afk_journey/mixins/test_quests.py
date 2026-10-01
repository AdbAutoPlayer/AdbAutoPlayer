from unittest.mock import MagicMock

import numpy as np
import pytest
from adb_auto_player.games.afk_journey.mixins.quests import (
    QuestMixin,
    is_afk_stage_title,
)
from adb_auto_player.models.template_matching import TemplateMatchResult


class _Stub(QuestMixin):
    """Minimal stub — template matching, OCR and navigation are mocked."""

    def __init__(self, title: str):
        self._quest_title_ocr_backend = MagicMock()
        self._quest_title_ocr_backend.extract_text.return_value = title
        self.get_screenshot = MagicMock(
            return_value=np.zeros((1920, 1080, 3), dtype=np.uint8)
        )
        # Typed MagicMock handles for assertions: the overridden attributes
        # keep the method signatures in the type checker's view
        self.find_mock = MagicMock()
        self.tap_mock = MagicMock()
        self.navigate_mock = MagicMock()
        self.capture_mock = MagicMock()
        self.find_any_template = self.find_mock
        self.tap = self.tap_mock
        self.handle_popup_messages = MagicMock()
        self.navigate_to_world = self.navigate_mock
        self.capture_debug_screenshot = self.capture_mock


def _start_battle_match() -> TemplateMatchResult:
    match = MagicMock(spec=TemplateMatchResult)
    match.template = "quests/start_battle"
    return match


class TestIsAfkStageTitle:
    @pytest.mark.parametrize(
        "title",
        [
            "AFK Stage 261①",
            "Season Phantimal Stage 536 6①",
            "Season Phantimal Stage 564①",
            "Season Phantimal Stage 564 0",
            "AFK Stage261",
        ],
    )
    def test_afk_stage_titles(self, title):
        assert is_afk_stage_title(title) is True

    @pytest.mark.parametrize(
        "title",
        ["Phantom Hauler Cabin (51) 42) ①", "Battle Story", "", "Backstage"],
    )
    def test_non_afk_stage_titles(self, title):
        assert is_afk_stage_title(title) is False


class TestStartBattleGuard:
    def test_afk_stages_screen_returns_to_world_without_battling(self, monkeypatch):
        monkeypatch.setattr(
            "adb_auto_player.games.afk_journey.mixins.quests.sleep", lambda _: None
        )
        bot = _Stub("AFK Stage 261")
        bot.find_mock.side_effect = [None, _start_battle_match()]

        assert bot._handle_dialogue_buttons(["quests/start_battle"]) is True

        bot.tap_mock.assert_not_called()
        bot.navigate_mock.assert_called_once()

    def test_story_battle_is_started(self, monkeypatch):
        monkeypatch.setattr(
            "adb_auto_player.games.afk_journey.mixins.quests.sleep", lambda _: None
        )
        bot = _Stub("Battle Story")
        match = _start_battle_match()
        bot.find_mock.side_effect = [None, match]

        assert bot._handle_dialogue_buttons(["quests/start_battle"]) is True

        bot.tap_mock.assert_called_once_with(match, scale=True)
        bot.navigate_mock.assert_not_called()


class TestBlindPopupTap:
    def test_screenshot_captured_before_blind_tap(self, monkeypatch):
        monkeypatch.setattr(
            "adb_auto_player.games.afk_journey.mixins.quests.sleep", lambda _: None
        )
        bot = _Stub("")
        bot.game_find_template_match = MagicMock(return_value=None)
        calls = MagicMock()
        calls.attach_mock(bot.capture_mock, "capture")
        calls.attach_mock(bot.tap_mock, "tap")

        bot._handle_stuck_state()

        assert [c[0] for c in calls.mock_calls] == ["capture", "tap"]
        bot.capture_mock.assert_called_once_with("quests_blind_popup_tap")
