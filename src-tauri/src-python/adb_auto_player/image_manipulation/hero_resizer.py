import argparse
import os

import cv2
import numpy as np
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.template_matching.template_matcher import TemplateMatcher
from adbutils import adb

MIN_DIMENSION = 10


def resize_hero_template(file_path, scale_factor=1 / 1.75):
    """Resizes a hero template to match the project's standard scale.

    Default scale factor is 1/1.75, which converts 1080p screenshots
    to the 720p-ish scale used by the AFK Stages scanner.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return False

    img = cv2.imread(str(file_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"Error: Failed to load image: {file_path}")
        return False

    new_width = int(img.shape[1] * scale_factor)
    new_height = int(img.shape[0] * scale_factor)

    # Use INTER_AREA for downscaling as it provides better results
    resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)

    cv2.imwrite(str(file_path), resized)
    print(
        f"Successfully resized {os.path.basename(file_path)} "
        f"to {new_width}x{new_height}"
    )
    return True


def find_optimal_scale(template_path, serial="127.0.0.1:5555", screenshot_path=None):
    """Tries multiple scales to find the one with the highest match confidence."""
    if screenshot_path and os.path.exists(screenshot_path):
        print(f"Using local screenshot: {screenshot_path}")
        ss = cv2.imread(screenshot_path)
    else:
        device = adb.device(serial=serial)
        pil_img = device.screenshot()
        ss = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    if ss is None:
        print("Error: Could not obtain screenshot.")
        return None

    template = cv2.imread(str(template_path), cv2.IMREAD_UNCHANGED)
    if template is None:
        print(f"Error: Failed to load template: {template_path}")
        return None

    matcher = TemplateMatcher()

    best_scale = None
    max_confidence = 0

    # Try scales from 0.4 to 0.8 (common range for 1080p to 720p-ish conversion)
    scales = [i / 100 for i in range(40, 81)]

    print(f"Calibrating scale for {os.path.basename(template_path)}...")
    for scale in scales:
        new_w = int(template.shape[1] * scale)
        new_h = int(template.shape[0] * scale)
        if new_w < MIN_DIMENSION or new_h < MIN_DIMENSION:
            continue

        resized_tpl = cv2.resize(template, (new_w, new_h), interpolation=cv2.INTER_AREA)
        result = matcher.find_template_match(
            ss, resized_tpl, threshold=ConfidenceValue("10%")
        )

        if result and result.confidence.value > max_confidence:
            max_confidence = result.confidence.value
            best_scale = scale
            # print(f"  New best: {scale:.2f} (Conf: {max_confidence*100:.1f}%)")

    if best_scale:
        print(
            f"Optimal scale found: {best_scale:.3f} "
            f"(Confidence: {max_confidence * 100:.1f}%)"
        )
        return best_scale

    print("Could not find a reliable match at any scale.")
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Resize hero templates for AFK Journey automation."
    )
    parser.add_argument("file", help="Path to the hero .png template")
    parser.add_argument(
        "--scale",
        type=float,
        help="Scale factor (if not provided, will auto-calibrate)",
    )
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Auto-calibrate scale against current screen",
    )
    parser.add_argument(
        "--serial", default="127.0.0.1:5555", help="ADB serial for calibration"
    )
    parser.add_argument(
        "--screenshot", help="Optional local screenshot path to use instead of adb"
    )

    args = parser.parse_args()

    target_scale = args.scale
    if args.calibrate or target_scale is None:
        target_scale = find_optimal_scale(args.file, args.serial, args.screenshot)

    if target_scale:
        resize_hero_template(args.file, target_scale)
