import logging
from dataclasses import dataclass
from time import sleep
from typing import ClassVar

from adb_auto_player.decorators import register_command
from adb_auto_player.exceptions import GameTimeoutError
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Point
from adb_auto_player.util import SummaryGenerator

from ..base import AFKJourneyBase


class TitanReaverProxyBattleConstants:
    """Constants related to proxy battles (currently for Titan Reaver only)."""

    KEYS_PER_BATTLE = 7  # Keys earned per battle

    # Timeout settings
    TEMPLATE_WAIT_TIMEOUT = 3  # Timeout for waiting for template appearance (seconds)
    NAVIGATION_DELAY = 1  # Navigation operation interval (seconds)

    # Exception handling
    MAX_EXCEPTION_COUNT = 10  # Maximum consecutive exceptions before reset

    # Offset values
    PROXY_BATTLE_BANNER_OFFSET_X = -70  # X offset for proxy battle banner tap
    PROXY_BATTLE_BANNER_OFFSET_Y = 190  # Y offset for proxy battle banner tap


@dataclass
class TitanReaverProxyBattleStats:
    """Proxy battle statistics with automatic SummaryGenerator updates."""

    battles_completed: int = 0
    exception_count: int = 0

    # Mapping from field name to display name
    _field_display_names: ClassVar[dict[str, str]] = {
        "battles_completed": "Battles Completed",
    }

    def __setattr__(self, name: str, value) -> None:
        """Adds values to Summary too."""
        super().__setattr__(name, value)

        # Only call SummaryGenerator.set for tracked fields with display names
        if name in self._field_display_names:
            display_name = self._field_display_names[name]
            SummaryGenerator.set("Titan Reaver Proxy Battle", display_name, value)
            if value > 0:
                if name == "battles_completed":
                    estimated_keys = (
                        value * TitanReaverProxyBattleConstants.KEYS_PER_BATTLE
                    )
                    SummaryGenerator.set(
                        "Titan Reaver Proxy Battle",
                        "Estimated Lucky Keys Earned",
                        estimated_keys,
                    )


class TitanReaverProxyBattleMixin(AFKJourneyBase):
    """Proxy battle Mixin, provides automation for proxy battles.

    (currently for Titan Reaver only)
    """

    @register_command(
        name="TitanReaverProxyBattle",
        gui=GUIMetadata(
            label="Titan Reaver Proxy Battle",
            category=AFKJCategory.EVENTS_AND_OTHER,
            tooltip="Automatically find and participate Titan Reaver proxy battles",
        ),
    )
    def proxy_battle(self) -> None:
        """Execute proxy battle automation."""
        self.start_up()

        logging.warning("Czesito has quit the game, this is no longer supported.")

        stats = TitanReaverProxyBattleStats()

        logging.info(
            "Starting Titan Reaver Proxy Battle automation (limit: "
            f"{self.get_config().titan_reaver_proxy_battles.proxy_battle_limit})"
        )

        try:
            while (
                stats.battles_completed
                < self.get_config().titan_reaver_proxy_battles.proxy_battle_limit
            ):
                if self._execute_single_proxy_battle():
                    stats.battles_completed += 1
                    stats.exception_count = 0
                    logging.info(f"Proxy Battle #{stats.battles_completed} completed")
                else:
                    stats.exception_count += 1
                    if (
                        stats.exception_count
                        >= TitanReaverProxyBattleConstants.MAX_EXCEPTION_COUNT
                    ):
                        logging.error(
                            "Too many consecutive failures, resetting to default state"
                        )
                        self.navigate_to_world()
                        stats.exception_count = 0
                    sleep(5)  # Wait longer after failure

        except KeyboardInterrupt as e:
            logging.info("Proxy Battle automation interrupted by user")
            raise e
        except Exception as e:
            logging.error(f"Unexpected error in proxy battle automation: {e}")

    def _execute_single_proxy_battle(self) -> bool:
        """Execute a single proxy battle.

        Returns:
            bool: Whether the battle was successfully completed
        """
        try:
            # Step 1: Navigate to team chat
            self.navigate_to_team_up_chat()

            # Step 2: Find proxy battle banner
            banner_location = self._find_proxy_battle_banner()
            if not banner_location:
                return False

            # Step 3: Join the battle
            if not self._join_proxy_battle(banner_location):
                return False

            # Step 4: Execute battle sequence
            return self._execute_battle_sequence()

        except GameTimeoutError as e:
            logging.warning(f"Timeout during proxy battle: {e}")
            return False

    def _find_proxy_battle_banner(self) -> Point | None:
        """Find proxy battle banner.

        Returns:
            Optional[Point]: Banner location, or None if not found
        """
        banner = self.find_any_template(
            templates=[
                "assist/proxy_battle_request.png",
            ],
            grayscale=True,
        )

        if banner is None:
            logging.info("No proxy battle banner found, swiping down to check for more")
            self.swipe_down(1000, 800, 1500)
            return None

        return Point(banner.x, banner.y)

    def _join_proxy_battle(self, banner_location: Point) -> bool:
        """Join proxy battle.

        Args:
            banner_location: Banner location

        Returns:
            bool: Whether successfully joined
        """
        logging.info("Found proxy battle banner, attempting to join")

        # Calculate click position
        click_point = Point(
            banner_location.x
            + TitanReaverProxyBattleConstants.PROXY_BATTLE_BANNER_OFFSET_X,
            banner_location.y
            + TitanReaverProxyBattleConstants.PROXY_BATTLE_BANNER_OFFSET_Y,
        )

        self.tap(click_point)
        sleep(TitanReaverProxyBattleConstants.NAVIGATION_DELAY)

        return True

    def _execute_battle_sequence(self) -> bool:
        """Execute battle sequence.

        Returns:
            bool: Whether the battle was successfully completed
        """
        battle_steps = [
            ("battle/battle.png", "battle button"),
            ("battle/formation_recommended.png", "recommended formation"),
            ("battle/use.png", "use formation button"),
            ("navigation/confirm_text.png", "confirm button"),
            ("battle/next.png", "next button"),
            ("battle/battle.png", "final battle button"),
            ("navigation/confirm.png", "final confirm button"),
            ("battle/skip.png", "skip button"),
        ]

        for template, description in battle_steps:
            if description in ("confirm button", "final confirm button"):
                # Special handling for confirm button
                if not self._wait_and_tap_template(template, description):
                    continue
            if not self._wait_and_tap_template(template, description):
                return False

        return True

    def _wait_and_tap_template(self, template: str, description: str) -> bool:
        """Wait for template to appear and tap.

        Args:
            template: Template path
            description: Template description (for logging)

        Returns:
            bool: Whether successfully found and tapped
        """
        try:
            result = self.wait_for_template(
                template, timeout=TitanReaverProxyBattleConstants.TEMPLATE_WAIT_TIMEOUT
            )

            self.tap(result)

            if template == "battle/skip.png":
                sleep(TitanReaverProxyBattleConstants.NAVIGATION_DELAY)

            logging.debug(f"Successfully tapped {description}")
            return True

        except GameTimeoutError:
            logging.warning(f"No {description} found within timeout")
            return False
