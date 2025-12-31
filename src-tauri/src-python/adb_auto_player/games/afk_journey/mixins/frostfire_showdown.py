"""AFK Journey Frostfire Showdown Mixin."""

import logging
from abc import ABC
from time import sleep


from adb_auto_player.decorators import register_command
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.models.template_matching import TemplateMatchResult


class FrostfireShowdownMixin(AFKJourneyBase, ABC):
    """Frostfire Showdown Mixin."""

    def __init__(self) -> None:
        """Initialize Frostfire Showdown Mixin."""
        super().__init__()
        self._defeat_counter = 0
        self._max_stamina = 3  # Default to Challenger difficulty
        self._max_retries = 3
        self._difficulty_name = "Unknown"
        self._failed_hero_teams = []  # Track heroes that failed in previous attempts
        self._last_selected_heroes = []  # Track the most recently selected team

    def _detect_difficulty(self) -> tuple[str, int, int]:
        """Detect the active difficulty level.
        
        Returns:
            Tuple of (difficulty_name, max_stamina, max_retries)
        """
        # Define difficulty configurations
        # Template name: (difficulty_name, max_stamina, max_retries)
        difficulty_configs = {
            "event/frostfire_showdown/difficulty_challenger": ("Challenger", 3, 3),
            "event/frostfire_showdown/difficulty_active_challenger": ("Challenger", 3, 3),
            "event/frostfire_showdown/difficulty_epic": ("Epic", 2, 2),
            "event/frostfire_showdown/difficulty_active_epic": ("Epic", 2, 2),
            "event/frostfire_showdown/difficulty_frostfire": ("Frostfire", 1, 1),
            "event/frostfire_showdown/difficulty_active_frostfire": ("Frostfire", 1, 1),
        }
        
        # Check for difficulty templates
        for template, config in difficulty_configs.items():
            result = self.game_find_template_match(
                template=template,
                threshold=ConfidenceValue("85%")
            )
            
            if result is not None:
                difficulty_name, max_stamina, max_retries = config
                logging.info(f"[Difficulty Detection] Detected {difficulty_name} difficulty (Max Stamina: {max_stamina}, Max Retries: {max_retries})")
                return config
        
        # Default to Challenger if no difficulty detected
        logging.warning("[Difficulty Detection] No difficulty detected, defaulting to Challenger (Max Stamina: 3, Max Retries: 3)")
        return ("Challenger", 3, 3)

    @register_command(
        name="FrostfireShowdown",
        gui=GUIMetadata(
            label="Run Frostfire Showdown",
            category=AFKJCategory.EVENTS_AND_OTHER,
        ),
    )
    def attempt_frostfire(self) -> None:
        """Attempt to run Frostfire Showdown Battles."""
        self.start_up()
        self.navigate_to_world()
        
        # Reset defeat counter at start
        self._defeat_counter = 0

        logging.info("Attempting to run Frostfire Showdown!")
        logging.warning(
            "EXPERIMENTAL, designed only to clear the shop. "
            "Prioritisies heroes based on what's currently visible"
        )

        if self._open_frostfire_showdown() is False:
            return

        while self._handle_battle():
            self._handle_battle()

        logging.info("Frostfire Showdown Finished!")

    def _open_frostfire_showdown(self) -> bool:
        logging.info(
            "Opening Frostfire Showdown",
        )
        self._tap_till_template_disappears(template="navigation/hamburger_menu")
        sleep(2)
        self._tap_till_template_disappears(template="dailies/hamburger/events")
        sleep(2)
        self._tap_till_template_disappears(
            template="event/frostfire_showdown/frostfire_showdown"
        )
        sleep(2)
        self.wait_for_template(template="event/frostfire_showdown/title_s")
        self.tap(Point(650, 1450))  # Join
        sleep(3)
        
        # Detect difficulty level
        difficulty_name, max_stamina, max_retries = self._detect_difficulty()
        self._difficulty_name = difficulty_name
        self._max_stamina = max_stamina
        self._max_retries = max_retries
        
        self.wait_for_template(template="event/frostfire_showdown/title_s")
        self.tap(Point(800, 1800))  # Start/Continue
        sleep(4)
        if self.game_find_template_match(
            template="event/frostfire_showdown/insufficient_resources"
        ):
            logging.warning("Out of Frostfire Showdown tokens!")
            return False
        return True

    def _handle_battle(self) -> bool:
        # Enter hero selection screen
        self.wait_for_template(template="event/frostfire_showdown/quick_select")
        self.tap(Point(800, 1800))  # Continue/Battle
        sleep(2)
        self._tap_till_template_disappears(template="navigation/confirm")  # consumables
        sleep(4)

        # Clear all hero spots
        self.wait_for_template(template="start_battle")
        logging.debug("Clearing heroes")
        self.tap(Point(425, 950))
        sleep(1)
        self.tap(Point(325, 870))
        sleep(1)
        self.tap(Point(175, 870))
        sleep(1)

        # Select 3 new ones from list of heroes (excluding previously failed heroes)
        self._handle_hero_selection(exclude_heroes=self._failed_hero_teams)

        # Start Battle
        self._tap_till_template_disappears(template="start_battle")  # Battle
        logging.info("Battling..")
        sleep(3)
        self._tap_till_template_disappears(template="navigation/confirm")  # Confirm
        sleep(15)

        # Handle end result
        if self._handle_battle_result():
            return True
        else:
            return False

    def _check_hero_stamina(self, hero_position: TemplateMatchResult) -> bool | None:
        """Check stamina indicator below detected hero.
        
        Args:
            hero_position: The template match result for the hero
            
        Returns:
            True: Hero has usable stamina (1/3, 2/3, or 3/3)
            False: Hero is depleted (0/3)
            None: No stamina indicator found (needs swipe)
        """
        hero_name = hero_position.template.split("/")[1].split("_")[0].capitalize()
        
        # Try with original dimensions first
        result = self._check_stamina_with_dimensions(hero_position, 200, 130, hero_name, attempt=1)
        if result is not None:
            return result
        
        # First retry: Increase dimensions by 30
        logging.debug(f"[Stamina Check] Retrying {hero_name} with enlarged crop area (+30px)")
        result = self._check_stamina_with_dimensions(hero_position, 230, 160, hero_name, attempt=2)
        if result is not None:
            return result
        
        # Second retry: Decrease dimensions by 30
        logging.debug(f"[Stamina Check] Retrying {hero_name} with reduced crop area (-30px)")
        result = self._check_stamina_with_dimensions(hero_position, 170, 100, hero_name, attempt=3)
        if result is not None:
            return result
        
        # All attempts failed
        logging.warning(f"[Stamina Check] No stamina indicator found for {hero_name} after 3 attempts - may be off screen")
        self.swipe_up(400, 1630, 1560, duration=1)
        sleep(1)
        return None
    
    def _check_stamina_with_dimensions(
        self, 
        hero_position: TemplateMatchResult, 
        stamina_area_width: int, 
        stamina_area_height: int,
        hero_name: str,
        attempt: int = 1
    ) -> bool | None:
        """Check stamina with specific crop dimensions.
        
        Args:
            hero_position: The template match result for the hero
            stamina_area_width: Width of search area
            stamina_area_height: Height of search area
            hero_name: Name of the hero (for logging)
            attempt: Attempt number (for logging)
            
        Returns:
            True: Hero has usable stamina (1/3, 2/3, or 3/3)
            False: Hero is depleted (0/3)
            None: No stamina indicator found
        """
        # Get display dimensions
        resolution = self.display_info.normalized_resolution
        
        # Define crop region below the hero icon
        # Hero icons are approximately 150px wide and 150px tall
        # Stamina bar is about 80-100px below the hero icon
        hero_x = hero_position.x - 40
        hero_y = hero_position.y
        
        stamina_y_offset = 125  # Distance vertical of the hero icon
        stamina_x_offset = 60  # Distance horizontal of the hero icon
        
        # Calculate crop values (in pixels)
        left_crop = max(0, hero_x + stamina_x_offset - stamina_area_width // 2)
        right_crop = max(0, resolution.width - (hero_x + stamina_x_offset + stamina_area_width // 2))
        top_crop = max(0, hero_y - stamina_y_offset)
        bottom_crop = max(0, resolution.height - (hero_y + stamina_y_offset + stamina_area_height))
        
        # Whoever the fuck made this CropRegions, this shit took forever to make work, it works, but I wish there was a better way
        crop_regions = CropRegions(
            left=f"{left_crop}px",
            right=f"{right_crop}px",
            top=f"{top_crop}px",
            bottom=f"{bottom_crop}px"
        )
        
        logging.debug(f"[Stamina Check] Attempt {attempt} for {hero_name} - dimensions: {stamina_area_width}x{stamina_area_height}")
        logging.debug(f"[Stamina Check] Crop region: left={left_crop}, right={right_crop}, top={top_crop}, bottom={bottom_crop}")
        
        # Build template lists dynamically based on detected difficulty
        depleted_template = f"event/frostfire_showdown/stamina_0-{self._max_stamina}"
        
        # Check if hero is depleted
        depleted_check = self.game_find_template_match(
            template=depleted_template,
            crop_regions=crop_regions,
            threshold=ConfidenceValue("85%")
        )
        
        if depleted_check is not None:
            stamina_level = depleted_template.split("_")[-1].replace(".png", "")
            logging.info(f"[Stamina Check] {hero_name} is DEPLETED ({stamina_level} stamina) - found on attempt {attempt}")
            return False
        
        # Build usable stamina templates based on max_stamina
        stamina_templates = [
            f"event/frostfire_showdown/stamina_{i}-{self._max_stamina}"
            for i in range(1, self._max_stamina + 1)
        ]
        
        for stamina_template in stamina_templates:
            stamina_check = self.game_find_template_match(
                template=stamina_template,
                crop_regions=crop_regions,
                threshold=ConfidenceValue("85%")
            )
            
            if stamina_check is not None:
                stamina_level = stamina_template.split("_")[-1].replace(".png", "")
                logging.info(f"[Stamina Check] {hero_name} has USABLE stamina ({stamina_level}) - found on attempt {attempt}")
                return True
        
        # No stamina indicator found with these dimensions
        return None

    def _handle_hero_selection(self, exclude_heroes=None):
        """Select heroes for battle, optionally excluding previously failed heroes.
        
        Args:
            exclude_heroes: List of hero template paths to exclude from selection
        """
        if exclude_heroes is None:
            exclude_heroes = []
            
        selected_heroes = 0
        selected_hero_names = []  # Track selected heroes for logging
        selected_hero_templates = []  # Track selected hero templates
        hero_slots = 3
        scrolls = 1
        max_scrolls = 20

        heroes = [
            "heroes/shakir_battle",  
            "heroes/daimon_battle",
            "heroes/talene_battle",
            "heroes/harak_battle",
            "heroes/tasi_battle",
            "heroes/shemira_battle",
            "heroes/marcille_battle",
            "heroes/lenya_battle",
            "heroes/sonja_battle",
            "heroes/vala_battle",
            "heroes/faramor_battle",
            "heroes/natsu_battle",
            "heroes/sinbad_battle",
            "heroes/berial_battle",
            "heroes/valka_battle",
        ]

        # # Reverse list for testing
        # heroes = [
        #     "heroes/silvina_battle",
        #     "heroes/valka_battle",
        #     "heroes/berial_battle",
        #     "heroes/sinbad_battle",
        #     "heroes/natsu_battle",
        #     "heroes/faramor_battle",
        #     "heroes/vala_battle",
        #     "heroes/sonja_battle",
        #     "heroes/lenya_battle",
        #     "heroes/shemira_battle",
        #     "heroes/harak_battle",
        #     "heroes/shakir_battle",
        # ]

        # Create a working copy of the heroes list that we can modify
        # Filter out excluded heroes (those that failed previously)
        available_heroes = [h for h in heroes if h not in exclude_heroes]
        
        if exclude_heroes:
            excluded_names = [h.split("/")[1].split("_")[0].capitalize() for h in exclude_heroes]
            logging.info(f"[Hero Selection] Excluding previously failed heroes: {', '.join(excluded_names)}")

        logging.info(f"[Hero Selection] Starting hero selection - need {hero_slots} heroes")
        
        while selected_heroes < hero_slots:
            logging.debug(f"[Hero Selection] Selected {selected_heroes}/{hero_slots} heroes, scroll attempt {scrolls}/{max_scrolls}")
            
            hero_checker = self.find_any_template(
                templates=available_heroes,
                threshold=ConfidenceValue(
                    "93%"
                ),  # Else Faramor triggers while already selected
            )
            
            if hero_checker is not None:
                hero_name = hero_checker.template.split("/")[1].split("_")[0].capitalize()
                logging.info(f"[Hero Selection] Found hero: {hero_name} at ({hero_checker.x}, {hero_checker.y})")
                
                # Check hero stamina
                stamina_status = self._check_hero_stamina(hero_checker)
                
                if stamina_status is None:
                    # No stamina indicator found - skip this hero for now
                    logging.warning(f"[Hero Selection] {hero_name} stamina indicator not visible, will retry after scrolling...")
                    # Don't remove from available_heroes - they might become visible after scrolling
                    continue  # Look for next hero
                    
                elif stamina_status is False:
                    # Hero is depleted (0/3 stamina)
                    logging.info(f"[Hero Selection] {hero_name} is depleted, skipping and looking for next hero...")
                    # Continue to find next hero without incrementing selected count
                    continue
                    
                else:  # stamina_status is True
                    # Hero has usable stamina, select it
                    scrolls = 1  # Reset scroll counter after successful selection
                    logging.info(f"[Hero Selection] Selecting {hero_name} (Hero {selected_heroes + 1}/{hero_slots})")
                    self.tap(hero_checker)
                    sleep(1)
                    selected_heroes += 1
                    selected_hero_names.append(hero_name)  # Track selected hero name
                    selected_hero_templates.append(hero_checker.template)  # Track selected hero template
                    available_heroes.remove(hero_checker.template)  # Prevent re-selection
                    
            elif scrolls <= max_scrolls:
                logging.info(f"[Hero Selection] No listed hero found on screen, scrolling down ({scrolls}/{max_scrolls})")
                self.swipe_up(400, 1630, 1485, duration=1)
                sleep(2)
                scrolls += 1
                
            if scrolls > max_scrolls:
                logging.error(f"[Hero Selection] Max scrolls reached! Only selected {selected_heroes}/{hero_slots} heroes. Resetting selection...")
                self.tap(Point(1000, 1625))
                self.tap(Point(715, 1600))
                self.tap(Point(850, 1600))
                self.tap(Point(1000, 1450))
                logging.info("[Hero Selection] Hero selection reset")
                return
        
        # Store the selected heroes for tracking failed teams
        self._last_selected_heroes = selected_hero_templates
        logging.info(f"[Hero Selection] Successfully selected all {hero_slots} heroes: {', '.join(selected_hero_names)}")

    def _handle_battle_result(self) -> bool:
        result = self.wait_for_any_template(
            templates=["event/frostfire_showdown/victory", "event/frostfire_showdown/defeat"],
            timeout=self.BATTLE_TIMEOUT,
            delay=1.0,
            timeout_message=self.BATTLE_TIMEOUT_ERROR_MESSAGE,
        )

        match result.template:
            case "event/frostfire_showdown/victory":
                logging.info("Victory!")
                # Reset defeat counter and failed heroes on victory
                self._defeat_counter = 0
                self._failed_hero_teams = []
                self.tap(Point(550, 1800))  # Tap to Close
                sleep(5)
                # If we won the final clear Battle Record and use next token
                if self.game_find_template_match(
                    template="event/frostfire_showdown/battle_record"
                ):
                    self.tap(Point(550, 1800))  # Tap Battle Record
                    sleep(5)
                    self.wait_for_template(template="event/frostfire_showdown/title_s")

                    # Detect difficulty level
                    difficulty_name, max_stamina, max_retries = self._detect_difficulty()
                    self._difficulty_name = difficulty_name
                    self._max_stamina = max_stamina
                    self._max_retries = max_retries
                    sleep(1)

                    self.tap(Point(800, 1800))  # Start/Continue
                    if self.game_find_template_match(
                        template="event/frostfire_showdown/insufficient_resources"
                    ):
                        logging.warning("Out of Frostfire Showdown tokens!")
                        return False
                return True

            case "event/frostfire_showdown/defeat":
                self._defeat_counter += 1
                logging.warning(f"Defeat! (Attempt {self._defeat_counter}/{self._max_retries})")
                
                # Track the failed hero team
                if self._last_selected_heroes:
                    self._failed_hero_teams.extend(self._last_selected_heroes)
                    failed_names = [h.split("/")[1].split("_")[0].capitalize() for h in self._last_selected_heroes]
                    logging.info(f"[Battle] Marking failed heroes to avoid: {', '.join(failed_names)}")
                
                self.tap(Point(550, 1800))  # Tap to Close
                sleep(5)
                
                # Retry with same token based on difficulty's max retries
                if self._defeat_counter <= self._max_retries:
                    logging.info("Retrying battle with different heroes...")
                    # Game automatically returns to battle selection screen after clicking close
                    return True
                
                # After max retries, view battle record and use a new token
                logging.info("Max retries reached, using a new token...")
                self.tap(Point(100, 1800))  # Tap back button on defeat screen
                sleep(3)
                self._defeat_counter = 0  # Reset counter for next token
                self._failed_hero_teams = []  # Reset failed heroes for new token
                self.tap(Point(550, 1800))  # Tap Battle Record
                sleep(5)
                # Use another token
                self.wait_for_template(template="event/frostfire_showdown/title_s")
                # Detect difficulty level
                difficulty_name, max_stamina, max_retries = self._detect_difficulty()
                self._difficulty_name = difficulty_name
                self._max_stamina = max_stamina
                self._max_retries = max_retries
                sleep(1)
                self.tap(Point(800, 1800))  # Start/Continue
                sleep(4)
                if self.game_find_template_match(
                    template="event/frostfire_showdown/insufficient_resources"
                ):
                    logging.warning("Out of Frostfire Showdown tokens!")
                    return False
                return True

        logging.warning("Something went wrong detecting battle results!")
        return False
