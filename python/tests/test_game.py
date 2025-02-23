import time
import unittest
from unittest.mock import patch, DEFAULT

from pathlib import Path
from adb_auto_player.exceptions import NotInitializedError
from adb_auto_player.game import Game
import adb_auto_player.template_matching as template_matching

TEST_DATA_DIR = Path(__file__).parent / "data"


class TestGame(unittest.TestCase):
    @patch.object(Game, "get_screenshot")
    def test_roi_has_changed(self, mock_get_screenshot):
        game = Game()
        with self.assertRaises(ValueError):
            game.roi_has_changed(0, 0, 0, 0)

        roi = (450, 280, 780, 400)
        f1 = TEST_DATA_DIR / "records_formation_1.png"
        f2 = TEST_DATA_DIR / "records_formation_2.png"

        game.previous_screenshot = template_matching.load_image(f1)
        mock_get_screenshot.return_value = template_matching.load_image(f1)

        # Missing scale factor
        with self.assertRaises(NotInitializedError):
            game.roi_has_changed(*roi)

        game.scale_factor = 1.0

        self.assertFalse(game.roi_has_changed(*roi))

        mock_get_screenshot.return_value = template_matching.load_image(f2)

        self.assertTrue(game.roi_has_changed(*roi))

    @patch.multiple(
        Game,
        get_screenshot=DEFAULT,
        get_template_dir_path=DEFAULT,
        get_resolution=DEFAULT,
    )
    def test_template_matching_speed(
        self,
        get_template_dir_path,
        get_screenshot,
        get_resolution,
    ):
        game = Game()

        base_image = TEST_DATA_DIR / "template_match_base.png"
        template_image = "template_match_template.png"

        get_screenshot.return_value = template_matching.load_image(base_image)
        get_template_dir_path.return_value = TEST_DATA_DIR
        get_resolution.return_value = (1080, 1920)

        full_times = []
        cropped_times = []
        full_results = []
        cropped_results = []
        crop_top = 0.9
        crop_right = 0.6
        crop_left = 0.1

        for _ in range(10):
            start_time = time.time()
            full_result = game.find_template_match(template_image)
            full_times.append(time.time() - start_time)
            full_results.append(full_result)

            start_time = time.time()
            cropped_result = game.find_template_match(
                template_image,
                crop_left=crop_left,
                crop_right=crop_right,
                crop_top=crop_top,
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

        print_output = (
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
