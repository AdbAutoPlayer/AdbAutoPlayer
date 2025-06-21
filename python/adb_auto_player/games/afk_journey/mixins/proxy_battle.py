import logging
from abc import ABC
from dataclasses import dataclass
from enum import IntEnum
from time import sleep
from typing import Optional

from adb_auto_player import GameTimeoutError
from adb_auto_player.decorators.register_command import GuiMetadata, register_command
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions


class TitanReaverProxyBattleConstants:
    """Constants related to proxy battles (currently for Titan Reaver only)"""
    
    # Calculation logic: Total number of lucky keys needed divided by keys earned per battle
    TOTAL_LUCKY_KEYS_NEEDED = 100 * 3 * 9  # Total keys needed to unlock all cards
    KEYS_PER_BATTLE = 7  # Keys earned per battle
    DEFAULT_BATTLE_LIMIT = TOTAL_LUCKY_KEYS_NEEDED // KEYS_PER_BATTLE
    
    # Timeout settings
    TEMPLATE_WAIT_TIMEOUT = 15  # Timeout for waiting for template appearance (seconds)
    RETRY_DELAY = 1  # Retry interval (seconds)
    NAVIGATION_DELAY = 1  # Navigation operation interval (seconds)
    
    # Coordinate constants
    CHAT_BUTTON_POINT = Point(1010, 1080)
    TEAM_UP_CHAT_POINT = Point(110, 850)
    WORLD_CHAT_POINT = Point(110, 350)
    
    # Offset values
    PROXY_BATTLE_BANNER_OFFSET_X = -70  # X offset for proxy battle banner tap
    PROXY_BATTLE_BANNER_OFFSET_Y = 190  # Y offset for proxy battle banner tap


@dataclass
class TitanReaverProxyBattleStats:
    """Proxy battle statistics"""
    battles_attempted: int = 0
    battles_completed: int = 0
    battles_failed: int = 0
    navigation_failures: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.battles_attempted == 0:
            return 0.0
        return (self.battles_completed / self.battles_attempted) * 100


class TitanReaverProxyBattleMixin(AFKJourneyBase, ABC):
    """Proxy battle Mixin, provides automation for proxy battles (currently for Titan Reaver only)"""

    @register_command(
        name="TitanReaverProxyBattle",
        gui=GuiMetadata(
            label="Proxy Battle",
            category=AFKJCategory.EVENTS_AND_OTHER,
            tooltip="Automatically participate in proxy battles"
        ),
    )
    def proxy_battle(self) -> None:
        """Execute proxy battle automation"""
        self.start_up()
        
        if self._stream is None:
            logging.warning(
                "This feature is quite slow without Device Streaming. "
                "You may miss proxy battle opportunities."
            )

        battle_limit = self._get_battle_limit()
        stats = TitanReaverProxyBattleStats()
        
        logging.info(f"Starting Proxy Battle automation (limit: {battle_limit})")
        
        try:
            while stats.battles_completed < battle_limit:
                stats.battles_attempted += 1
                
                if self._execute_single_proxy_battle():
                    stats.battles_completed += 1
                    logging.info(f"Proxy Battle #{stats.battles_completed} completed")
                else:
                    # stats.battles_failed += 1
                    # logging.warning(f"Proxy Battle attempt #{stats.battles_attempted} failed")
                    sleep(5)  # Wait longer after failure
                    
        except KeyboardInterrupt:
            logging.info("Proxy Battle automation interrupted by user")
        except Exception as e:
            logging.error(f"Unexpected error in proxy battle automation: {e}")
        finally:
            self._log_final_stats(stats)

    def _get_battle_limit(self) -> int:
        """Get battle limit"""
        try:
            # Try to fetch from configuration, use default value if not available
            return getattr(self.get_config().general, 'proxy_battle_limit', 
                          TitanReaverProxyBattleConstants.DEFAULT_BATTLE_LIMIT)
        except AttributeError:
            return TitanReaverProxyBattleConstants.DEFAULT_BATTLE_LIMIT

    def _execute_single_proxy_battle(self) -> bool:
        """Execute a single proxy battle
        
        Returns:
            bool: Whether the battle was successfully completed
        """
        try:
            # Step 1: Navigate to team chat
            if not self._navigate_to_team_chat():
                return False
                
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

    def _navigate_to_team_chat(self) -> bool:
        """Navigate to team chat
        
        Returns:
            bool: Whether navigation was successful
        """
        # Check if already in team chat
        if self._is_in_team_chat():
            return True
            
        # Check if in other chat channels
        if self._is_in_other_chat():
            self._switch_to_team_chat()
            return self._is_in_team_chat()
            
        # Requires re-navigation
        logging.info("Navigating to Team-Up Chat")
        self.navigate_to_default_state()
        self.tap(TitanReaverProxyBattleConstants.CHAT_BUTTON_POINT, scale=True)
        sleep(TitanReaverProxyBattleConstants.NAVIGATION_DELAY)
        self.tap(TitanReaverProxyBattleConstants.TEAM_UP_CHAT_POINT, scale=True)
        
        return False  # Requires next loop to check again

    def _is_in_team_chat(self) -> bool:
        """Check if in team chat"""
        return self.find_any_template(
            templates=[
                "assist/label_team-up_chat.png",
            ],
        ) is not None

    def _is_in_other_chat(self) -> bool:
        """Check if in other chat channels"""
        return self.find_any_template([
            "assist/tap_to_enter.png",
            "assist/label_world_chat.png"
        ]) is not None

    def _switch_to_team_chat(self) -> None:
        """Switch to team chat"""
        self.tap(TitanReaverProxyBattleConstants.TEAM_UP_CHAT_POINT, scale=True)
        sleep(TitanReaverProxyBattleConstants.NAVIGATION_DELAY)

    def _find_proxy_battle_banner(self) -> Optional[Point]:
        """Find proxy battle banner
        
        Returns:
            Optional[Point]: Banner location, or None if not found
        """
        banner = self.find_any_template(
            templates=[
                "assist/proxy_battle_request.png",
            ]
        )
        
        if banner is None:
            logging.info("No proxy battle banner found, swiping down to check for more")
            self._swipe_chat_down()
            return None
            
        return Point(banner.x, banner.y)

    def _swipe_chat_down(self) -> None:
        """Swipe down the chat window"""
        self.swipe_down(1000, 500, 1500)
        sleep(TitanReaverProxyBattleConstants.NAVIGATION_DELAY)

    def _join_proxy_battle(self, banner_location: Point) -> bool:
        """Join proxy battle
        
        Args:
            banner_location: Banner location
            
        Returns:
            bool: Whether successfully joined
        """
        logging.info("Found proxy battle banner, attempting to join")
        
        # Calculate click position
        click_point = Point(
            banner_location.x + TitanReaverProxyBattleConstants.PROXY_BATTLE_BANNER_OFFSET_X,
            banner_location.y + TitanReaverProxyBattleConstants.PROXY_BATTLE_BANNER_OFFSET_Y
        )
        
        self.tap(click_point)
        sleep(TitanReaverProxyBattleConstants.NAVIGATION_DELAY)
        
        return True

    def _execute_battle_sequence(self) -> bool:
        """Execute battle sequence
        
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
            ("battle/skip.png", "skip button")
        ]
        
        for template, description in battle_steps:
            if description == "confirm button" or description == "final confirm button":
                # Special handling for confirm button
                if not self._wait_and_tap_template(template, description):
                    continue
            if not self._wait_and_tap_template(template, description):
                return False
                
        return True

    def _wait_and_tap_template(self, template: str, description: str) -> bool:
        """Wait for template to appear and tap
        
        Args:
            template: Template path
            description: Template description (for logging)
            
        Returns:
            bool: Whether successfully found and tapped
        """
        try:
            result = self.wait_for_template(
                template,
                timeout=TitanReaverProxyBattleConstants.TEMPLATE_WAIT_TIMEOUT
            )
            
            self.tap(result)
            
            if template == "battle/skip.png":
                sleep(TitanReaverProxyBattleConstants.NAVIGATION_DELAY)
                
            logging.debug(f"Successfully tapped {description}")
            return True
            
        except GameTimeoutError:
            logging.warning(f"No {description} found within timeout")
            return False

    def _log_final_stats(self, stats: TitanReaverProxyBattleStats) -> None:
        """Log final statistics"""
        logging.info("Proxy Battle Automation Summary:")
        logging.info(f"  Battles Attempted: {stats.battles_attempted}")
        logging.info(f"  Battles Completed: {stats.battles_completed}")
        # logging.info(f"  Battles Failed: {stats.battles_failed}")
        logging.info(f"  Success Rate: {stats.success_rate:.1f}%")
        
        if stats.battles_completed > 0:
            estimated_keys = stats.battles_completed * TitanReaverProxyBattleConstants.KEYS_PER_BATTLE
            logging.info(f"  Estimated Lucky Keys Earned: {estimated_keys}")
