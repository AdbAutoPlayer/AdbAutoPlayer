import logging
from datetime import datetime, timedelta
from enum import Enum, auto
from time import sleep, monotonic, perf_counter

import cv2
import numpy as np
from adb_auto_player.decorators import register_command
from adb_auto_player.device.adb import ATTranslatedSet2Keyboard, BlueStacksVirtualTouch, XiaomiJoystick

from adb_auto_player.exceptions import AutoPlayerUnrecoverableError, AutoPlayerError
from adb_auto_player.image_manipulation import IO, Cropping
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.models.template_matching import TemplateMatchResult
from adb_auto_player.template_matching import TemplateMatcher

from .blue_protocol_star_resonance import BlueProtocolStarResonance


class HorizontalDirection(Enum):
    """Enum representing horizontal directions."""

    LEFT = auto()
    CENTER = auto()
    RIGHT = auto()


class Fishing(BlueProtocolStarResonance):
    FISHING_POLE_BUTTON = Point(1740, 890)
    FISHING_POLE_INVENTORY_BUTTON = Point(400, 960)
    BAIT_INVENTORY_BUTTON = Point(250, 960)

    fish_caught_count = 0
    joystick_direction: HorizontalDirection = HorizontalDirection.CENTER
    is_reeling: bool = False
    joystick: XiaomiJoystick | None = None
    keyboard: ATTranslatedSet2Keyboard | None = None
    virtual_touch: BlueStacksVirtualTouch | None = None

    A = BlueStacksVirtualTouch.get_input_event_codes()["A"]
    D = BlueStacksVirtualTouch.get_input_event_codes()["D"]

    @register_command(
        gui=GUIMetadata(
            label="Fishing",
        ),
        name="BPSR.fishing",
    )
    def entry(self) -> None:
        self.disable_debug_screenshots = True
        self.start_stream()
        self.close_popups()

        self.select_steering_method()
        self.select_reeling_method()

        if result := self.game_find_template_match("fishing/fishing.png"):
            self.tap(result)
            sleep(5)


        while True:
            if not self.is_fishing_minigame_ready():
                self.close_popups()
                if not self.is_fishing_minigame_ready():
                    raise AutoPlayerUnrecoverableError("Not inside fishing minigame")

            self.fishing_loop()

    def select_steering_method(self) -> None:
        try:
            self.joystick = XiaomiJoystick()
            self.joystick.l_stick.release(force=True)
            logging.info("Using Xiaomi Joystick")
            return
        except AutoPlayerError:
            self.joystick = None

        try:
            self.keyboard = ATTranslatedSet2Keyboard()
            self.keyboard.ev_syn()
            logging.info("Using AT Translated Set 2 Keyboard")
            return
        except AutoPlayerError:
            self.keyboard = None
        raise AutoPlayerUnrecoverableError(
            "Cannot initialize Xiaomi Joystick or AT Translated Set 2 Keyboard for steering"
        )

    def select_reeling_method(self) -> None:
        try:
            self.virtual_touch = BlueStacksVirtualTouch(self.display_info)
            self.virtual_touch.release()

            iterations = 10
            vt_times = []
            for _ in range(iterations):
                start = perf_counter()
                self.virtual_touch.release()
                vt_times.append(perf_counter() - start)
            avg_vt_time = sum(vt_times) / iterations

            # Benchmark MotionEvent
            me_times = []
            for _ in range(iterations):
                start = perf_counter()
                self.device.hold_release(self.FISHING_POLE_BUTTON)
                me_times.append(perf_counter() - start)
            avg_me_time = sum(me_times) / iterations

            if avg_me_time < avg_vt_time:
                self.virtual_touch = None
                logging.info(
                    "Using ADB input motionevent for reeling (%.6f s vs %.6f s)",
                    avg_me_time, avg_vt_time
                )
            else:
                logging.info(
                    "Using BlueStacks Virtual Touch for reeling (%.6f s vs %.6f s)",
                    avg_vt_time, avg_me_time
                )
        except AutoPlayerError:
            self.virtual_touch = None
            self.device.hold_release(self.FISHING_POLE_BUTTON)
            logging.info("Using BlueStacks Virtual Touch for reeling")
        return

    def is_fishing_pole_broken(self) -> bool:
        cropped = Cropping.crop_to_box(
            self.get_screenshot(),
            Box(
                top_left=Point(444, 898),
                width=12,
                height=12,
            ),
        )

        return TemplateMatcher.similar_image(
            cropped.image,
            IO.load_image(self.template_dir / "fishing" / "exclamation_mark.png"),
        )

    def equip_or_buy_bait(self) -> None:
        self.tap(self.BAIT_INVENTORY_BUTTON)
        sleep(1)
        btn = self.wait_for_any_template(
            ["fishing/use.png", "fishing/go_to_purchase.png"]
        )
        self.tap(btn)

        if btn.template == "fishing/use.png":
            sleep(1)
            return

        bait = self.wait_for_any_template(
            self.get_templates_from_dir("fishing/store/bait")
        )
        self.tap(bait)
        sleep(5)
        purchase = self.wait_for_template("fishing/store/purchase.png")
        self.tap(purchase)
        sleep(2)
        self.press_back_button()
        sleep(2)
        return

    def is_bait_empty(self) -> bool:
        cropped = Cropping.crop_to_box(
            self.get_screenshot(),
            Box(
                top_left=Point(294, 898),
                width=12,
                height=12,
            ),
        )

        return TemplateMatcher.similar_image(
            cropped.image,
            IO.load_image(self.template_dir / "fishing" / "exclamation_mark.png"),
        )

    def equip_or_buy_fishing_pole(self) -> None:
        self.tap(self.FISHING_POLE_INVENTORY_BUTTON)
        sleep(1)
        btn = self.wait_for_any_template(
            ["fishing/use.png", "fishing/go_to_purchase.png"]
        )
        self.tap(btn)

        if btn.template == "fishing/use.png":
            sleep(1)
            return

        fishing_pole = self.wait_for_any_template(
            self.get_templates_from_dir("fishing/store/fishing_poles")
        )
        self.tap(fishing_pole)
        sleep(5)
        purchase = self.wait_for_template("fishing/store/purchase.png")
        self.tap(purchase)
        sleep(2)
        self.press_back_button()
        sleep(2)
        return

    def fishing_loop(self) -> None:
        self.equip_or_buy_fishing_gear()
        self.tap(self.FISHING_POLE_BUTTON)
        if not self.fish_hooked():
            return

        self.tap(self.FISHING_POLE_BUTTON)
        self.catch_fish()
        sleep(1)

    def equip_or_buy_fishing_gear(self) -> None:
        while self.is_fishing_pole_broken():
            self.equip_or_buy_fishing_pole()

        while self.is_bait_empty():
            self.equip_or_buy_bait()

    def fish_hooked(
        self,
        min_box_area_correct_color_percentage: float = 0.7,
    ) -> bool:
        timeout = datetime.now() + timedelta(seconds=30)
        while datetime.now() < timeout:
            fish_hooked_exclamation_mark = Box(
                top_left=Point(943, 548),
                width=28,
                height=24,
            )

            if (
                get_color_match_percentage(
                    image=Cropping.crop_to_box(
                        self.get_screenshot(),
                        fish_hooked_exclamation_mark,
                    ).image,
                    min_red=240,
                    max_green=120,
                    max_blue=20,
                )
                >= min_box_area_correct_color_percentage
            ):
                return True
            sleep(0.1)
        return False

    def catch_fish(self) -> None:
        start_time = monotonic()
        timeout = 15
        while not self.is_ready_to_reel():
            if monotonic() - start_time > timeout:
                logging.error("Failed to start reeling")
                return
            pass

        self.start_reeling()
        while True:
            if self.step_joystick_towards_fish():
                sleep(1)
                self.start_reeling()
                continue

            if self.get_continue_fishing_button():
                self.fish_caught_count += 1
                logging.info(f"Fish caught: {self.fish_caught_count}")
                break

            if self.is_fishing_pole_inventory_button_visible():
                logging.warning("Failed to catch fish")
                break
            sleep(1 / 30)

        self.release()

    def release(self):
        if self.keyboard:
            self.keyboard.release(self.D)
            self.keyboard.release(self.A)
        self.stop_reeling()

        match self.joystick_direction:
            case HorizontalDirection.LEFT:
                self.step_right()
            case HorizontalDirection.CENTER:
                pass
            case HorizontalDirection.RIGHT:
                self.step_left()
        return

    def start_reeling(self) -> None:
        if not self.is_reeling:
            if self.virtual_touch:
                self.virtual_touch.hold(self.FISHING_POLE_BUTTON)
            else:
                self.device.hold_down(self.FISHING_POLE_BUTTON)
            self.is_reeling = True

    def stop_reeling(self) -> None:
        if self.is_reeling:
            if self.virtual_touch:
                self.virtual_touch.release()
            else:
                self.device.hold_release(self.FISHING_POLE_BUTTON)
            self.is_reeling = False

    def step_joystick_towards_fish(
        self,
        min_box_area_correct_color_percentage: float = 0.5,
        min_red: int = 220,
        max_green: int = 150,
        max_blue: int = 30,
    ) -> bool:
        left_help_arrow_box = Box(
            top_left=Point(815, 530),
            width=50,
            height=25,
        )

        if (
            get_color_match_percentage(
                image=Cropping.crop_to_box(
                    self.get_screenshot(),
                    left_help_arrow_box,
                ).image,
                min_red=min_red,
                max_green=max_green,
                max_blue=max_blue,
            )
            >= min_box_area_correct_color_percentage
        ):
            self.step_left()
            return True

        right_help_arrow_box = Box(
            top_left=Point(1050, 530),
            width=50,
            height=25,
        )

        if (
            get_color_match_percentage(
                image=Cropping.crop_to_box(
                    self.get_screenshot(),
                    right_help_arrow_box,
                ).image,
                min_red=min_red,
                max_green=max_green,
                max_blue=max_blue,
            )
            >= min_box_area_correct_color_percentage
        ):
            self.step_right()
            return True
        return False

    def is_ready_to_reel(self):
        cropped = Cropping.crop_to_box(
            self.get_screenshot(),
            Box(
                top_left=Point(1270, 883),
                width=24,
                height=24,
            ),
        )

        return TemplateMatcher.similar_image(
            cropped.image,
            IO.load_image(self.template_dir / "fishing" / "fish.png"),
        )

    def is_fishing_minigame_ready(self) -> bool:
        if btn := self.get_continue_fishing_button():
            self.tap(btn)
            sleep(2)

        return self.is_fishing_pole_inventory_button_visible()

    def get_continue_fishing_button(self) -> TemplateMatchResult | None:
        return self.game_find_template_match(
            "fishing/continue_fishing.png",
            crop_regions=CropRegions(
                left="70%",
                top="80%",
            ),
        )

    def is_fishing_pole_inventory_button_visible(self) -> bool:
        return (
            self.find_any_template(
                self.get_templates_from_dir("fishing/fishing_poles"),
                crop_regions=CropRegions(
                    top="80%",
                    right="70%",
                ),
            )
            is not None
            or self.is_fishing_pole_broken()
        )

    def step_left(self) -> None:
        self.stop_reeling()
        match self.joystick_direction:
            case HorizontalDirection.LEFT:
                pass
            case HorizontalDirection.CENTER:
                if self.joystick:
                    self.joystick.l_stick.hold_left()
                else:
                    self.keyboard.hold(self.A)
                self.joystick_direction = HorizontalDirection.LEFT
            case HorizontalDirection.RIGHT:
                    if self.joystick:
                        self.joystick.l_stick.release()
                    else:
                        self.keyboard.release(self.D)
                    self.joystick_direction = HorizontalDirection.CENTER
        pass

    def step_right(self) -> None:
        self.stop_reeling()
        match self.joystick_direction:
            case HorizontalDirection.LEFT:
                if self.joystick:
                    self.joystick.l_stick.release()
                else:
                    self.keyboard.release(self.A)
                self.joystick_direction = HorizontalDirection.CENTER
            case HorizontalDirection.CENTER:
                if self.joystick:
                    self.joystick.l_stick.hold_right()
                else:
                    self.keyboard.hold(self.D)
                self.joystick_direction = HorizontalDirection.RIGHT
            case HorizontalDirection.RIGHT:
                pass
        return


def get_color_match_percentage(
    image: np.ndarray,
    min_red: int = 240,
    max_green: int = 150,
    max_blue: int = 20,
) -> float:
    """Returns the percentage of pixels that match the color."""
    b, g, r = cv2.split(image)
    mask = (r >= min_red) & (g <= max_green) & (b <= max_blue)
    return np.sum(mask) / mask.size
