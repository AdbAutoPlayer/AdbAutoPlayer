from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from adb_auto_player.exceptions import GameTimeoutError
from adb_auto_player.file_loader.settings_loader import SettingsLoader
from adb_auto_player.games.afk_journey.mixins.afk_stages import AFKStagesMixin
from adb_auto_player.games.afk_journey.mixins.arcane_labyrinth import (
    ArcaneLabyrinthMixin,
)
from adb_auto_player.games.afk_journey.mixins.assist import AssistMixin
from adb_auto_player.games.afk_journey.mixins.dailies import DailiesMixin
from adb_auto_player.games.afk_journey.mixins.duras_trials import DurasTrialsMixin
from adb_auto_player.games.afk_journey.mixins.frostfire_showdown import (
    FrostfireShowdownMixin,
)
from adb_auto_player.games.afk_journey.mixins.homestead_helper import (
    HomesteadHelperMixin,
)
from adb_auto_player.games.afk_journey.mixins.quests import QuestMixin
from adb_auto_player.games.afk_journey.mixins.ravaged_realm import RavagedRealmMixin
from adb_auto_player.games.afk_journey.mixins.start_afk_journey import StartAFKJourney
from adb_auto_player.games.afk_journey.mixins.sunlit_showdown import SunlitShowdownMixin
from adb_auto_player.games.afk_journey.mixins.titan_reaver_proxy_battle import (
    TitanReaverProxyBattleMixin,
)
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.ocr import OCRResult
from adb_auto_player.models.template_matching import TemplateMatchResult


class MockAllAFKJ(
    AFKStagesMixin,
    ArcaneLabyrinthMixin,
    AssistMixin,
    DailiesMixin,
    DurasTrialsMixin,
    FrostfireShowdownMixin,
    HomesteadHelperMixin,
    QuestMixin,
    RavagedRealmMixin,
    StartAFKJourney,
    SunlitShowdownMixin,
    TitanReaverProxyBattleMixin,
):
    def __init__(self):
        self._settings = MagicMock()
        # Mock settings structure
        self._settings.general.assist_limit = 1
        self._settings.afk_stages.use_suggested_formations = False
        self._settings.homestead.craft_item_limit = 0
        self._settings.arcane_labyrinth.key_quota = 0
        self._settings.arcane_labyrinth.difficulty = 1
        self._settings.dailies.arena_battle = False
        self._settings.dailies.raise_affinity = False
        self._settings.dailies.duras_trials = False
        self._settings.dailies.buy_discount_affinity = False
        self._settings.dailies.buy_all_affinity = False
        self._settings.dailies.buy_essences = False
        self._settings.dailies.single_pull = False
        self._settings.legend_trials.towers = []
        self._settings.guild_manager_scan.days_to_scan = 3
        self.battle_state = MagicMock()
        self.battle_state.section_header = "Test Stage"
        self._stream = MagicMock()
        self._device = MagicMock()
        self._device.get_running_app.return_value = "com.farlightgames.igame.gp"
        self._target_package_name = "com.farlightgames.igame.gp"
        self._failed_hero_teams = []
        self.default_threshold = ConfidenceValue("90%")
        self.LANG_ERROR = "error"
        self.BATTLE_TIMEOUT = 1
        self._screenshot_dir = None  # disable debug screenshot saving in tests

    @property
    def fast_timeout(self):
        return 1.0

    @property
    def min_timeout(self):
        return 1.0

    @property
    def settings(self):
        return self._settings

    @property
    def template_dir(self):
        return MagicMock()

    @property
    def _hero_scanner(self):
        return MagicMock()

    def get_screenshot(self):
        return MagicMock()

    def tap(self, *args, **kwargs):
        pass

    def wait_for_template(self, *args, **kwargs):
        return MagicMock()

    def wait_for_any_template(self, *args, **kwargs):
        return MagicMock()

    def game_find_template_match(self, *args, **kwargs):
        return None

    def swipe_up(self, *args, **kwargs):
        pass

    def sleep_navigation(self):
        pass

    def start_up(self, *args, **kwargs):
        pass

    def navigate_to_afk_stages_screen(self):
        pass

    def check_stages_are_available(self):
        pass

    def _select_afk_stage(self):
        pass

    def _handle_battle_screen(self, *args, **kwargs):
        return False

    def _start_arcane_labyrinth(self, *args, **kwargs):
        pass

    def claim_daily_rewards(self, *args, **kwargs):
        pass

    def buy_emporium(self, *args, **kwargs):
        pass

    def single_pull(self, *args, **kwargs):
        pass

    def claim_hamburger(self, *args, **kwargs):
        pass

    def swap_essences(self, *args, **kwargs):
        pass

    def _enter_dr(self, *args, **kwargs):
        pass

    def _select_duras_trials_tower(self, *args, **kwargs):
        pass

    def _open_frostfire_showdown(self, *args, **kwargs):
        pass

    def navigate_to_homestead(self, *args, **kwargs):
        pass

    def _find_quest_images(self, *args, **kwargs):
        return False

    def _enter_ravaged_realm(self, *args, **kwargs):
        pass

    def _open_sunlit_showdown(self, *args, **kwargs):
        pass

    def _execute_single_proxy_battle(self, *args, **kwargs):
        pass

    def navigate_to_battle_modes_screen(self, *args, **kwargs):
        pass

    def _find_in_battle_modes(self, *args, **kwargs):
        return MagicMock()

    def navigate_to_world(self, *args, **kwargs):
        pass

    def sleep_action(self, *args, **kwargs):
        pass


def test_push_afk_stages():
    bot = MockAllAFKJ()
    with patch.object(bot, "start_up"):
        bot.push_afk_stages(season=False)
        bot.push_afk_stages(season=True)


def test_push_afk_stages_timeout_fallback():
    bot = MockAllAFKJ()

    def mock_wait(*args, **kwargs):
        raise GameTimeoutError("Mock timeout")

    with patch.object(bot, "start_up"):
        with patch.object(bot, "wait_for_template", side_effect=mock_wait):
            bot.push_afk_stages(season=False)
            bot.push_afk_stages(season=True)


def test_run_arcane_labyrinth():
    bot = MockAllAFKJ()
    with patch.object(bot, "start_up"):
        with patch.object(bot, "_start_arcane_labyrinth"):
            bot.handle_arcane_labyrinth()


def test_assist_synergy_corrupt_creature():
    bot = MockAllAFKJ()
    with patch.object(bot, "start_up"):
        with patch.object(bot, "_find_synergy_or_corrupt_creature", return_value=True):
            bot.assist_synergy_corrupt_creature()


def test_claim_dailies():
    SettingsLoader.set_app_config_dir(Path("."))
    SettingsLoader.set_resource_dir(Path("."))
    bot = MockAllAFKJ()
    with (
        patch.object(bot, "start_up"),
        patch.object(bot, "navigate_to_world"),
        patch.object(bot, "claim_daily_rewards"),
        patch.object(bot, "buy_emporium"),
        patch.object(bot, "single_pull"),
        patch.object(bot, "run_dream_realm"),
        patch.object(bot, "claim_hamburger"),
        patch.object(bot, "swap_essences"),
        patch.object(bot, "push_afk_stages"),
    ):
        bot.run_dailies()


def test_run_dream_realm():
    bot = MockAllAFKJ()
    with patch.object(bot, "start_up"):
        with (
            patch.object(bot, "_enter_dr"),
            patch.object(bot, "_stop_condition", return_value=False),
        ):
            bot.run_dream_realm()


def test_push_duras_trials():
    bot = MockAllAFKJ()
    with (
        patch.object(bot, "start_up"),
        patch.object(bot, "navigate_to_duras_trials_screen"),
    ):
        with patch.object(bot, "_select_duras_trials_tower"):
            bot.push_duras_trials()


def test_run_frostfire_showdown():
    bot = MockAllAFKJ()
    with patch.object(bot, "start_up"), patch.object(bot, "navigate_to_world"):
        with patch.object(bot, "_open_frostfire_showdown"):
            bot.attempt_frostfire()


def test_run_hero_scanner():
    bot = MockAllAFKJ()
    with patch.object(bot, "start_up"):
        bot.scan_roster()


def test_run_homestead_helper():
    bot = MockAllAFKJ()
    with patch.object(bot, "start_up"):
        with patch.object(bot, "navigate_to_homestead"):
            bot.navigate_production_buildings_for_crafting()


def test_run_quests():
    bot = MockAllAFKJ()
    with patch.object(bot, "start_up"):
        with (
            patch.object(bot, "_find_quest_images", return_value=False),
            patch("time.sleep"),
        ):
            bot.attempt_quests()


def test_run_ravaged_realm():
    bot = MockAllAFKJ()
    with patch.object(bot, "start_up"):
        with patch.object(bot, "_enter_ravaged_realm"):
            bot.run_ravaged_realm()


def test_run_ravaged_realm_skip():
    """Skip path: _try_skip returns True → _run_all_squads still runs."""
    bot = MockAllAFKJ()
    with (
        patch.object(bot, "start_up"),
        patch.object(bot, "_enter_ravaged_realm"),
        patch.object(bot, "_try_skip", return_value=True),
        patch.object(bot, "_run_all_squads") as mock_squads,
        patch("time.sleep"),
    ):
        bot.run_ravaged_realm()
        mock_squads.assert_called_once()


def test_run_all_squads_skips_disabled_factions():
    """Factions not in configured_squads are skipped without any tap."""
    bot = MockAllAFKJ()
    bot._settings.ravaged_realm = MagicMock()
    bot._settings.ravaged_realm.squads = []  # all disabled

    with (
        patch.object(bot, "_run_battle") as mock_battle,
        patch("time.sleep"),
    ):
        bot._run_all_squads()
        mock_battle.assert_not_called()


def test_run_all_squads_runs_enabled_faction():
    """An enabled faction with a Battle button present triggers _run_battle."""
    bot = MockAllAFKJ()
    bot._settings.ravaged_realm = MagicMock()
    bot._settings.ravaged_realm.squads = ["Graveborn"]

    battle_match = TemplateMatchResult(
        template="battle/battle.png",
        confidence=ConfidenceValue("90%"),
        box=Box(Point(0, 0), 100, 50),
    )

    with (
        patch.object(bot, "game_find_template_match", return_value=battle_match),
        patch.object(bot, "_run_battle") as mock_battle,
        patch.object(bot, "swipe_right"),
        patch("time.sleep"),
    ):
        bot._run_all_squads()
        mock_battle.assert_called_once()


def test_run_all_squads_skips_locked_squad():
    """A faction where Battle button is absent (locked) is skipped."""
    bot = MockAllAFKJ()
    bot._settings.ravaged_realm = MagicMock()
    bot._settings.ravaged_realm.squads = ["Graveborn"]

    with (
        patch.object(bot, "game_find_template_match", return_value=None),
        patch.object(bot, "_run_battle") as mock_battle,
        patch.object(bot, "swipe_right"),
        patch("time.sleep"),
    ):
        bot._run_all_squads()
        mock_battle.assert_not_called()


def test_run_all_squads_scrolls_right_for_non_graveborn():
    """Non-Graveborn factions trigger a swipe_left to reach State 2."""
    bot = MockAllAFKJ()
    bot._settings.ravaged_realm = MagicMock()
    bot._settings.ravaged_realm.squads = ["Mauler"]

    with (
        patch.object(bot, "game_find_template_match", return_value=None),
        patch.object(bot, "swipe_left") as mock_swipe_left,
        patch("time.sleep"),
    ):
        bot._run_all_squads()
        mock_swipe_left.assert_called_once()


def test_start_afk_journey():
    bot = MockAllAFKJ()
    with patch.object(bot, "start_game"):
        bot.start_afk_journey()


def test_run_sunlit_showdown():
    bot = MockAllAFKJ()
    with patch.object(bot, "start_up"), patch.object(bot, "navigate_to_world"):
        with patch.object(bot, "_open_sunlit_showdown"):
            bot.attempt_sunlit()


def test_run_titan_reaver():
    bot = MockAllAFKJ()
    with patch.object(bot, "start_up"):
        with patch.object(bot, "_execute_single_proxy_battle"):
            bot.proxy_battle()


def test_scan_supreme_arena():
    bot = MockAllAFKJ()
    with (
        patch.object(bot, "navigate_to_battle_modes_screen"),
        patch.object(bot, "_find_in_battle_modes", return_value=Point(100, 100)),
        patch.object(bot, "tap"),
        patch.object(bot, "wait_for_template", return_value=Point(200, 200)),
        patch.object(bot, "_set_guild_members_filter", return_value=True),
        patch.object(bot, "game_find_template_match", return_value=None),
        patch.object(
            bot,
            "_scan_rankings_for_current_date",
            return_value=[{"Rank": "1", "Name": "PlayerA", "Date": "Monday"}],
        ),
        patch.object(
            bot,
            "_correct_names_with_guild_members",
            return_value=[{"Rank": "1", "Name": "PlayerA", "Date": "Monday"}],
        ),
        patch("builtins.open", mock_open()),
    ):
        bot._scan_supreme_arena(MagicMock(), MagicMock(), [])


def test_navigate_to_guild_members_screen_success():
    """Guild tab found by OCR -> swipe -> Members button found -> returns True."""
    bot = MockAllAFKJ()

    guild_tab_result = OCRResult(
        text="Guild",
        box=Box(Point(731, 1874), 78, 32),
        confidence=ConfidenceValue("99%"),
    )
    members_btn_result = OCRResult(
        text="Members",
        box=Box(Point(622, 276), 240, 58),
        confidence=ConfidenceValue("99%"),
    )

    ocr_mock = MagicMock()
    ocr_mock.detect_text_blocks.side_effect = [
        [guild_tab_result],  # first call: looking for Guild tab
        [members_btn_result],  # second call: looking for Members button
    ]

    with (
        patch.object(bot, "tap"),
        patch.object(bot.device, "swipe"),
        patch("time.sleep"),
    ):
        result = bot._navigate_to_guild_members_screen(ocr_mock)

    assert result is True


def test_navigate_to_guild_members_screen_failure():
    """Guild tab not found even after navigate_to_world -> returns False."""
    bot = MockAllAFKJ()

    ocr_mock = MagicMock()
    ocr_mock.detect_text_blocks.return_value = []  # never finds anything

    with (
        patch.object(bot, "navigate_to_world"),
        patch.object(bot, "tap"),
        patch.object(bot.device, "swipe"),
        patch("time.sleep"),
    ):
        result = bot._navigate_to_guild_members_screen(ocr_mock)

    assert result is False


def test_scan_guild_activeness():
    """Full guild activeness scan: navigate succeeds, rows parsed, JSON saved."""
    bot = MockAllAFKJ()

    sample_pairs = [("BlackFriday", "1280"), ("Mikki", "1280")]

    with (
        patch.object(bot, "_navigate_to_guild_members_screen", return_value=True),
        patch.object(
            bot,
            "_parse_activeness_rows",
            side_effect=[
                sample_pairs,
                # remaining scrolls return empty -> triggers early stop
                [],
                [],
                [],
                [],
                [],
            ],
        ),
        patch.object(bot, "_save_guild_activeness_to_json") as mock_save,
        patch.object(bot, "swipe_up"),
        patch("time.sleep"),
    ):
        bot._scan_guild_activeness(MagicMock(), [])

    mock_save.assert_called_once()
    saved_records = mock_save.call_args[0][0]
    assert len(saved_records) == 2
    assert saved_records[0]["Name"] == "BlackFriday"
    assert saved_records[0]["Activeness"] == 1280
