"""Pytest Game Module."""

import math
import time
import unittest
from pathlib import Path
from unittest.mock import DEFAULT, patch

from adb_auto_player.exceptions import GameTimeoutError
from adb_auto_player.game import Game
from adb_auto_player.image_manipulation import IO
from adb_auto_player.models.device import DisplayInfo, Orientation
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.models.template_matching import TemplateMatchResult
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

    def _load_config(self) -> None:
        """Mocked method."""
        pass

    def get_config(self) -> BaseModel:
        """Mocked method."""
        return MockConfig()

    @property
    def scale_factor(self) -> float:
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

        start_image = IO.load_image(TEST_DATA_DIR / "records_formation_1.png")

        with self.assertRaises(ValueError):
            game.wait_for_roi_change(
                start_image=start_image,
                crop_regions=CropRegions(left=-0.5),
            )

        with self.assertRaises(ValueError):
            game.wait_for_roi_change(
                start_image=start_image,
                crop_regions=CropRegions(left=1.5),
            )

        with self.assertRaises(ValueError):
            game.wait_for_roi_change(
                start_image=start_image,
                crop_regions=CropRegions(left=0.8, right=0.5),
            )

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

        start_image = IO.load_image(f1)
        get_screenshot.return_value = IO.load_image(f1)

        with self.assertRaises(GameTimeoutError):
            game.wait_for_roi_change(
                start_image=start_image,
                timeout=1.0,
            )

        get_screenshot.return_value = IO.load_image(f2)
        self.assertTrue(game.wait_for_roi_change(start_image=start_image, timeout=0))

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

        start_image = IO.load_image(f1)
        get_screenshot.return_value = IO.load_image(f1)

        with self.assertRaises(GameTimeoutError):
            game.wait_for_roi_change(
                start_image=start_image,
                crop_regions=CropRegions(left=0.2, right=0.2, top=0.15, bottom=0.8),
                timeout=1.0,
            )

        get_screenshot.return_value = IO.load_image(f2)
        self.assertTrue(
            game.wait_for_roi_change(
                start_image=start_image,
                crop_regions=CropRegions(left=0.2, right=0.2, top=0.15, bottom=0.8),
                timeout=0,
            )
        )

    @patch.multiple(
        Game,
        get_screenshot=DEFAULT,
        get_template_dir_path=DEFAULT,
        display_info=DEFAULT,
    )
    def test_template_matching_speed(
        self,
        get_template_dir_path,
        get_screenshot,
        display_info,
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

        get_screenshot.return_value = IO.load_image(base_image)
        get_template_dir_path.return_value = TEST_DATA_DIR
        display_info.return_value = DisplayInfo(
            width=1080, height=1920, orientation=Orientation.PORTRAIT
        )

        full_times = []
        cropped_times = []
        full_results: list[TemplateMatchResult] = []
        cropped_results: list[TemplateMatchResult] = []
        crop = CropRegions(top=0.9, right=0.6, left=0.1)

        for _ in range(10):
            start_time: float = time.time()
            full_result = game.game_find_template_match(template_image)
            if not full_result:
                assert False
            full_times.append(time.time() - start_time)
            full_results.append(full_result)

            start_time = time.time()
            cropped_result = game.game_find_template_match(
                template_image, crop_regions=crop
            )
            if not cropped_result:
                assert False
            cropped_times.append(time.time() - start_time)
            cropped_results.append(cropped_result)

        self.assertTrue(
            all(cropped < full for cropped, full in zip(cropped_times, full_times)),
            msg="Cropped matching should be faster than full matching",
        )

        for cropped, full in zip(cropped_results, full_results):
            self.assertEqual(
                cropped.template, full.template, msg="Template names should match"
            )
            self.assertEqual(cropped.box, full.box, msg="Bounding boxes should match")
            self.assertTrue(
                math.isclose(cropped.confidence, full.confidence, rel_tol=1e-2),
                msg=(
                    "Confidences should be close: "
                    f"{cropped.confidence} vs {full.confidence}"
                ),
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
