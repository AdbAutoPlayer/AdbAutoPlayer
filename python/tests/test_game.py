"""Pytest Game Module."""

import time
import unittest
from pathlib import Path
from unittest.mock import DEFAULT, patch

from adb_auto_player import (
    Command,
    CropRegions,
    Game,
    NoPreviousScreenshotError,
    TimeoutError,
)
from adb_auto_player.ipc.game_gui import GameGUIOptions
from adb_auto_player.template_matching import load_image
from pydantic import BaseModel

TEST_DATA_DIR: Path = Path(__file__).parent / "data"


class MockConfig(BaseModel):
    """Mock Config class."""

    pass


class MockGame(Game):
    """Mock Game class."""

    def get_template_dir_path(self) -> Path:
        """Mocked method."""
        return TEST_DATA_DIR

    def load_config(self) -> None:
        """Mocked method."""
        pass

    def get_cli_menu_commands(self) -> list[Command]:
        """Mocked method."""
        return []

    def get_gui_options(self) -> GameGUIOptions:
        """Mocked method."""
        return GameGUIOptions(
            game_title="Dummy Game",
            config_path="dummy_config_path",
            menu_options=[],
            constraints={},
        )

    def get_supported_resolutions(self) -> list[str]:
        """Mocked method."""
        return ["1080x1920"]

    def get_config(self) -> BaseModel:
        """Mocked method."""
        return MockConfig()

    def get_scale_factor(self) -> float:
        """Mocked method."""
        return 1.0


class TestGame(unittest.TestCase):
    """Test Game class."""

    def test_wait_for_roi_change_validation(self) -> None:
        """Test validation in wait_for_roi_change.

        Verifies that wait_for_roi_change will raise the appropriate exceptions
        when given invalid input.
        """
        game = MockGame()

        with self.assertRaises(NoPreviousScreenshotError):
            game.wait_for_roi_change()

        game.previous_screenshot = load_image(TEST_DATA_DIR / "records_formation_1.png")

        with self.assertRaises(ValueError):
            game.wait_for_roi_change(crop=CropRegions(left=-0.5))

        with self.assertRaises(ValueError):
            game.wait_for_roi_change(crop=CropRegions(left=1.5))

        with self.assertRaises(ValueError):
            game.wait_for_roi_change(crop=CropRegions(left=0.8, right=0.5))

    @patch.object(Game, "get_screenshot")
    def test_wait_for_roi_change_no_crop(self, get_screenshot) -> None:
        """Test wait_for_roi_change without cropping.

        This test checks the behavior of wait_for_roi_change when the entire
        image is used (no cropping applied). It ensures that the function
        raises a TimeoutError when no change occurs and returns True when a
        change is detected. The Game.get_screenshot method is patched to
        simulate different screenshots.
        """
        game = MockGame()

        f1: Path = TEST_DATA_DIR / "records_formation_1.png"
        f2: Path = TEST_DATA_DIR / "records_formation_2.png"

        game.previous_screenshot = load_image(f1)
        get_screenshot.return_value = load_image(f1)

        with self.assertRaises(TimeoutError):
            game.wait_for_roi_change(timeout=1.0)

        get_screenshot.return_value = load_image(f2)
        self.assertTrue(game.wait_for_roi_change(timeout=0))

    @patch.object(Game, "get_screenshot")
    def test_wait_for_roi_change_with_crop(self, get_screenshot) -> None:
        """Test wait_for_roi_change with cropping.

        This test checks the behavior of wait_for_roi_change when cropping is
        applied. It ensures that the function raises a TimeoutError when no
        change occurs and returns True when a change is detected. The
        Game.get_screenshot method is patched to simulate different
        screenshots.
        """
        game = MockGame()

        f1: Path = TEST_DATA_DIR / "records_formation_1.png"
        f2: Path = TEST_DATA_DIR / "records_formation_2.png"

        game.previous_screenshot = load_image(f1)
        get_screenshot.return_value = load_image(f1)

        with self.assertRaises(TimeoutError):
            game.wait_for_roi_change(
                crop=CropRegions(left=0.2, right=0.2, top=0.15, bottom=0.8), timeout=1.0
            )

        get_screenshot.return_value = load_image(f2)
        self.assertTrue(
            game.wait_for_roi_change(
                crop=CropRegions(left=0.2, right=0.2, top=0.15, bottom=0.8), timeout=0
            )
        )

    @patch.multiple(
        Game,
        get_screenshot=DEFAULT,
        get_template_dir_path=DEFAULT,
        resolution=DEFAULT,
    )
    def test_template_matching_speed(
        self,
        get_template_dir_path,
        get_screenshot,
        resolution,
    ) -> None:
        """Test performance of template matching with and without cropping.

        This test evaluates the speed and accuracy of the `find_template_match`
        method when applied to full images versus cropped images. It patches
        the `Game` class methods to simulate different scenarios, and compares
        the execution time and results of template matching with both full and
        cropped images.

        The test asserts that:
        - Cropped template matching is faster than full image matching.
        - The results of both full and cropped template matching are identical.

        The performance metrics (min, max, and average time) and results of
        each matching approach are printed at the end of the test.
        """
        game = MockGame()

        base_image: Path = TEST_DATA_DIR / "template_match_base.png"
        template_image = "template_match_template.png"

        get_screenshot.return_value = load_image(base_image)
        get_template_dir_path.return_value = TEST_DATA_DIR
        resolution.return_value = (1080, 1920)

        full_times = []
        cropped_times = []
        full_results = []
        cropped_results = []
        crop = CropRegions(top=0.9, right=0.6, left=0.1)

        for _ in range(10):
            start_time: float = time.time()
            full_result: tuple[int, int] | None = game.game_find_template_match(
                template_image
            )
            full_times.append(time.time() - start_time)
            full_results.append(full_result)

            start_time = time.time()
            cropped_result: tuple[int, int] | None = game.game_find_template_match(
                template_image, crop=crop
            )
            cropped_times.append(time.time() - start_time)
            cropped_results.append(cropped_result)

        self.assertTrue(
            all(cropped < full for cropped, full in zip(cropped_times, full_times)),
            msg="Cropped matching should be faster than full matching",
        )

        self.assertEqual(
            cropped_results,
            full_results,
            msg="Cropped results should be identical to full results",
        )

        print_output: str = (
            "\n"
            "test_template_matching_speed:\n"
            f"Full Image Matching Min Time: {min(full_times):.6f} "
            f"Max Time: {max(full_times):.6f} "
            f"Avg Time: {sum(full_times) / 10:.6f}\n"
            f"Cropped Image Matching Min Time: {min(cropped_times):.6f} "
            f"Max Time: {max(cropped_times):.6f} "
            f"Avg Time: {sum(cropped_times) / 10:.6f}\n"
            f"Full Image Matching Results: {full_results}\n"
            f"Cropped Image Matching Results: {cropped_results}\n"
        )
        self.addCleanup(lambda: print(print_output))
