import logging
from time import sleep

from adb_auto_player.decorators import (
    register_custom_routine_choice,
)
from adb_auto_player.exceptions import (
    AutoPlayerError,
    AutoPlayerUnrecoverableError,
    GameActionFailedError,
    GameTimeoutError,
)
from adb_auto_player.log import LogPreset
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.models.template_matching import TemplateMatchResult
from adb_auto_player.util import StringHelper

from ..base import AFKJourneyBase


class EquipNewEquipment(AFKJourneyBase):
    _EQUIPMENT_POINT = Point(970, 1660)
    _EQUIPMENT_TEMPLATES = (
        "equipment/support.png",
        "equipment/mage.png",
        "equipment/warrior.png",
        "equipment/rogue.png",
        "equipment/marksman.png",
        "equipment/tank.png",
    )
    _EQUIPMENT_TEMPLATE_THRESHOLD = ConfidenceValue("80%")
    _EQUIPMENT_TEMPLATE_CROP_REGIONS = CropRegions(
        top="40%",
        bottom="20%",
        left="20%",
        right="20%",
    )
    _EQUIPMENT_QUICK_EQUIP_CROP_REGIONS = CropRegions(
        top="70%",
        bottom="10%",
        left="10%",
        right="10%",
    )

    @register_custom_routine_choice("Equip new Equipment")
    def _equip_new_equipment(self) -> None:
        self.start_up()
        logging.info("Checking for new Equipment.")

        self._navigate_to_equipment_screen()

        equipment_classes = []
        for template in self._EQUIPMENT_TEMPLATES:
            if result := self.game_find_template_match(
                template=template,
                crop_regions=self._EQUIPMENT_TEMPLATE_CROP_REGIONS,
                threshold=self._EQUIPMENT_TEMPLATE_THRESHOLD,
            ):
                equipment_classes.append(result)

        if not equipment_classes:
            raise GameActionFailedError("Could not find Equipment Class Buttons.")

        not_found_count = 0
        max_not_found_count = 3
        count = 0
        max_count = 10

        equipment_found = False
        while not_found_count < max_not_found_count and count < max_count:
            if btn := self.game_find_template_match(
                "navigation/resonating_hall_back.png",
                crop_regions=CropRegions(top="80%", right="80%"),
            ):
                self.tap(btn)
                sleep(3)
            count += 1
            result = self.find_any_template(
                templates=[
                    "equipment/exclamation_mark_1.png",
                    "equipment/exclamation_mark_2.png",
                ],
                crop_regions=self._EQUIPMENT_TEMPLATE_CROP_REGIONS,
                threshold=self._EQUIPMENT_TEMPLATE_THRESHOLD,
            )
            if result is None:
                not_found_count += 1
                sleep(0.1)
                continue
            self._find_and_equip_new_equipment(result, equipment_classes)
            equipment_found = True
            if btn := self.game_find_template_match(
                "navigation/resonating_hall_back.png",
                crop_regions=CropRegions(top="80%", right="80%"),
            ):
                self.tap(btn)
                sleep(3)
        if not equipment_found:
            logging.info(
                "No new Equipment found.",
                extra={"preset": LogPreset.NOT_AVAILABLE},
            )

    def _find_and_equip_new_equipment(
        self,
        exclamation_mark: TemplateMatchResult,
        equipment_classes: list[TemplateMatchResult],
    ) -> None:
        candidates = [
            eq
            for eq in equipment_classes
            if eq.box.center.y > exclamation_mark.box.center.y
        ]

        if not candidates:
            logging.debug(
                f"Should not happen\n"
                f"ExclamationMark: {exclamation_mark}\n"
                f"EquipmentClasses: {equipment_classes}"
            )
            return

        closest_equipment_class = min(
            equipment_classes,
            key=lambda eq: exclamation_mark.box.center.distance_to(eq.box.center),
        )

        if not closest_equipment_class:
            logging.debug(
                f"Should not happen\n"
                f"ExclamationMark: {exclamation_mark}\n"
                f"EquipmentClasses: {equipment_classes}"
            )
            return

        self._equip(closest_equipment_class)
        return

    def _equip(self, equipment_class: TemplateMatchResult) -> None:
        class_str = StringHelper.get_filename_without_extension(
            equipment_class.template
        ).capitalize()

        logging.debug(f"Found new {class_str} Equipment")

        count = 0
        max_count = 3
        while count < max_count:
            count += 1
            if class_icon := self.game_find_template_match(
                equipment_class.template,
                crop_regions=self._EQUIPMENT_TEMPLATE_CROP_REGIONS,
                threshold=self._EQUIPMENT_TEMPLATE_THRESHOLD,
            ):
                self.tap(class_icon)
            try:
                quick_equip = self.wait_for_template(
                    template="equipment/quick_equip.png",
                    crop_regions=self._EQUIPMENT_QUICK_EQUIP_CROP_REGIONS,
                    threshold=self._EQUIPMENT_TEMPLATE_THRESHOLD,
                    timeout=self.MIN_TIMEOUT,
                )
                self.tap(quick_equip)
                self.wait_until_template_disappears(
                    template="equipment/quick_equip.png",
                    crop_regions=self._EQUIPMENT_QUICK_EQUIP_CROP_REGIONS,
                    threshold=self._EQUIPMENT_TEMPLATE_THRESHOLD,
                    timeout=self.FAST_TIMEOUT,
                )
                logging.info(f"{class_str} Equipment equipped")
                self.press_back_button()
                sleep(5)
                return
            except GameTimeoutError:
                continue

        logging.warning(f"Failed to equip {class_str} Equipment")
        self.press_back_button()
        sleep(3)
        return

    def _navigate_to_equipment_screen(self) -> None:
        max_count = 3
        count = 0
        while True:
            if count > max_count:
                raise AutoPlayerUnrecoverableError("Cannot find Equipment screen.")
            try:
                self.navigate_to_resonating_hall()
                self.tap(self._EQUIPMENT_POINT)
                templates = ["equipment/open_all.png", *self._EQUIPMENT_TEMPLATES]
                _ = self.wait_for_any_template(
                    templates=templates,
                    crop_regions=self._EQUIPMENT_TEMPLATE_CROP_REGIONS,
                    threshold=self._EQUIPMENT_TEMPLATE_THRESHOLD,
                )
                # The equipment class templates can be visible for a brief moment
                # before the open all pop up fades in
                sleep(1)

                result = self.wait_for_any_template(
                    templates=templates,
                    crop_regions=self._EQUIPMENT_TEMPLATE_CROP_REGIONS,
                    threshold=self._EQUIPMENT_TEMPLATE_THRESHOLD,
                )

                open_all_count = 0
                max_open_all_count = 3
                while (
                    result.template == "equipment/open_all.png"
                    and open_all_count < max_open_all_count
                ):
                    count += 1
                    logging.info("Opening Equipment Chests.")
                    self.tap(result)
                    # Close the next Popup showing the Equipment
                    sleep(2)
                    self.tap(result)
                    result = self.wait_for_any_template(
                        templates=templates,
                        crop_regions=self._EQUIPMENT_TEMPLATE_CROP_REGIONS,
                        threshold=self._EQUIPMENT_TEMPLATE_THRESHOLD,
                    )

                break
            except AutoPlayerError:
                count += 1
