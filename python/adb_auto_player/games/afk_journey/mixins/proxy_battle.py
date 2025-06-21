"""AFK Journey Proxy Battle Mixin."""

import logging
import time
from abc import ABC
from time import sleep

from adb_auto_player import GameTimeoutError
from adb_auto_player.decorators.register_command import GuiMetadata, register_command
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions


class ProxyBattleMixin(AFKJourneyBase, ABC):
    """Proxy Battle Mixin for automated proxy battle functionality."""

    @register_command(
        name="ProxyBattle",
        gui=GuiMetadata(
            label="Proxy Battle",
            category=AFKJCategory.EVENTS_AND_OTHER,
            tooltip="Automatically participate in proxy battles"
        ),
    )
    def proxy_battle(self) -> None:
        """Execute proxy battle automation."""
        self.start_up()

        if self._stream is None:
            logging.warning(
                "This feature is quite slow without Device Streaming "
                "you may miss proxy battle opportunities"
            )

        # proxy_battle_limit = self.get_config().general.proxy_battle_limit
        self.proxy_battle_limit: int = 100 * 3 * 9 // 7  # Total lucky keys needed to unlock all cards divided by 7 (key earned per battle)
        logging.info("Starting Proxy Battle automation")
        self._count: int = 0
        
        while self._count < self.proxy_battle_limit:
            if self._find_and_join_proxy_battle():
                logging.info(f"Proxy Battle #{self._count} completed")
            else:
                # Wait a bit before trying again
                sleep(5)

        logging.info("Finished: Proxy Battle")

    def _find_and_join_proxy_battle(self) -> bool:  # noqa: PLR0911 - TODO
        """Find and join available proxy battles."""
        result = self.find_any_template(
            templates=[
                # "assist/label_world_chat.png",
                # "assist/tap_to_enter.png",
                "assist/label_team-up_chat.png",
            ],
        )

        if result is None:
            logging.info("Navigating to Team-Up Chat")
            self.navigate_to_default_state()
            self.tap(Point(1010, 1080), scale=True)
            sleep(1)
            self.tap(Point(110, 850), scale=True)
            return False

        match result.template:
            # Chat Window is open but not on World Chat
            case "assist/tap_to_enter.png", "assist/label_world_chat.png":
                self.tap(Point(110, 350), scale=True)
                return False
            case "assist/label_team-up_chat.png":
                pass

        proxy_battle_banner = self.find_any_template(
            templates=[
                "assist/proxy_battle_request.png",
            ],
        )
        
        if proxy_battle_banner is None:
            logging.info("No proxy battle banner found, swiping down to check for more")
            self.swipe_down(1000, 500, 1500)
            sleep(1)
            return False

        # Join the proxy battle
        logging.info("Found proxy battle banner, attempting to join")
        self.tap(Point(proxy_battle_banner.x - 70, proxy_battle_banner.y + 190))
        sleep(1)

        # Join the battle
        for sec in range(15):
            battle_button = self.find_any_template(
            templates=[
                "battle/battle.png",
            ],
            )
            if battle_button is not None:
                self.tap(battle_button)
                break
            else:
                sleep(1)
        if battle_button is None:
            logging.warning("No battle button found, cannot proceed")
            return False

        for sec in range(15):
            formation_recommended = self.find_any_template(
                templates=[
                    "battle/formation_recommended.png",
                ],
            )
            if formation_recommended is not None:
                self.tap(formation_recommended)
                break
            else:
                sleep(1)
        
        if formation_recommended is None:
            logging.warning("No recommended formation button found, cannot proceed")
            return False
        
        for sec in range(15):
            use_formation = self.find_any_template(
                templates=[
                    "battle/use.png",
                ],
            )
            if use_formation is not None:
                self.tap(use_formation)
                logging.info("Using the first available formation")
                break
            else:
                sleep(1)
        if use_formation is None:
            logging.warning("No use button found, cannot proceed")
            return False
    
        for sec in range(15):
            next_button = self.find_any_template(
            templates=[
                "battle/next.png",
            ],
            )
            if next_button is not None:
                self.tap(next_button)
                break
            else:
                sleep(1)
        if next_button is None:
            logging.warning("No next button found, cannot proceed")
            return False

        for sec in range(15):
            battle_button = self.find_any_template(
            templates=[
                "battle/battle.png",
            ],
            )
            if battle_button is not None:
                self.tap(battle_button)
                break
            else:
                sleep(1)
        if battle_button is None:
            logging.warning("No battle button found, cannot proceed")
            return False
        
        for sec in range(15):
            skip_button = self.find_any_template(
                templates=[
                    "battle/skip.png",
                ],
            )
            if skip_button is not None:
                self.tap(skip_button)
                sleep(1)
                self._count += 1
                return True
            else:
                sleep(1)
        if skip_button is None:
            logging.warning("No skip button found, cannot proceed")
            return False
        return False