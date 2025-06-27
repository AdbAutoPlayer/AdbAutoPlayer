import time

import cv2
import numpy as np


def find_colors_fast(img):
    h, w = img.shape[:2]

    # Define thirds
    top_third = img[0 : h // 3, :]
    middle_third = img[h // 3 : 2 * h // 3, :]

    # === TOP THIRD: Find specific color RGB(244, 222, 105) ===
    target_color = np.array([105, 222, 244])  # BGR format
    tolerance = 15  # Adjust as needed

    # Create mask for target color with tolerance
    lower_bound = np.maximum(target_color - tolerance, 0)
    upper_bound = np.minimum(target_color + tolerance, 255)

    top_mask = cv2.inRange(top_third, lower_bound, upper_bound)

    # Find contours for bounding box
    contours, _ = cv2.findContours(top_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    top_result = None
    if contours:
        # Get largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w_box, h_box = cv2.boundingRect(largest_contour)
        top_result = (x, y, x + w_box, y + h_box)  # (x1, y1, x2, y2)

    # === MIDDLE THIRD: Find icon with color range ===
    # Define color range in BGR
    lower_orange = np.array([81, 196, 255])  # RGB(255, 196, 81) -> BGR
    upper_orange = np.array([83, 212, 255])  # RGB(255, 212, 83) -> BGR

    # Create mask for orange range
    middle_mask = cv2.inRange(middle_third, lower_orange, upper_orange)

    # Find 100px wide section with most color occurrences
    best_x = 0
    max_count = 0

    # Slide 100px window across width
    window_width = 100
    for x in range(0, w - window_width + 1, 5):  # Step by 5 for speed
        window_mask = middle_mask[:, x : x + window_width]
        count = np.sum(window_mask > 0)

        if count > max_count:
            max_count = count
            best_x = x

    middle_result = (
        (best_x, h // 3, best_x + window_width, 2 * h // 3) if max_count > 0 else None
    )

    return top_result, middle_result


# Usage example
def process_image(imag):
    top_bbox, middle_bbox = find_colors_fast(img)

    print("Top third color detection:")
    if top_bbox:
        print(f"  Bounding box: {top_bbox}")
    else:
        print("  Color not found")

    print("Middle third icon detection:")
    if middle_bbox:
        print(f"  Best 100px section: x={middle_bbox[0]} to x={middle_bbox[2]}")
    else:
        print("  Icon colors not found")

    return top_bbox, middle_bbox


# Optimized version for even faster processing
def find_colors_ultra_fast(image_path):
    """Ultra-fast version with additional optimizations"""
    img = cv2.imread(image_path)
    h, w = img.shape[:2]

    # Work with smaller image for initial detection
    scale = 0.5
    small_img = cv2.resize(img, (int(w * scale), int(h * scale)))
    small_h, small_w = small_img.shape[:2]

    # Define thirds on small image
    top_third = small_img[0 : small_h // 3, :]
    middle_third = small_img[small_h // 3 : 2 * small_h // 3, :]

    # Top third detection (scaled)
    target_color = np.array([105, 222, 244])
    tolerance = 20
    lower_bound = np.maximum(target_color - tolerance, 0)
    upper_bound = np.minimum(target_color + tolerance, 255)

    top_mask = cv2.inRange(top_third, lower_bound, upper_bound)
    contours, _ = cv2.findContours(top_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    top_result = None
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w_box, h_box = cv2.boundingRect(largest_contour)
        # Scale back to original coordinates
        top_result = (
            int(x / scale),
            int(y / scale),
            int((x + w_box) / scale),
            int((y + h_box) / scale),
        )

    # Middle third detection with faster sliding window
    lower_orange = np.array([81, 196, 255])
    upper_orange = np.array([83, 212, 255])
    middle_mask = cv2.inRange(middle_third, lower_orange, upper_orange)

    # Use integral image for fast window sum calculation
    integral = cv2.integral(middle_mask.astype(np.uint8))

    best_x = 0
    max_count = 0
    window_width = int(100 * scale)  # Scale window size

    for x in range(0, small_w - window_width + 1, 10):  # Larger steps for speed
        # Fast sum using integral image
        count = (
            integral[small_h // 3, x + window_width]
            - integral[small_h // 3, x]
            - integral[0, x + window_width]
            + integral[0, x]
        )

        if count > max_count:
            max_count = count
            best_x = x

    # Scale back coordinates
    middle_result = (
        (int(best_x / scale), h // 3, int((best_x + window_width) / scale), 2 * h // 3)
        if max_count > 0
        else None
    )

    return top_result, middle_result


# Example usage
if __name__ == "__main__":
    image_path = "img.png"

    start_time = time.time()

    # Load image
    img = cv2.imread(image_path)

    # Use regular version
    top_bbox, middle_bbox = find_colors_fast(img)

    # Or use ultra-fast version for maximum speed
    # top_bbox, middle_bbox = find_colors_ultra_fast(image_path)

    process_image(img)
    end_time = time.time()
    print(f"Time taken to load and process image: {end_time - start_time:.4f} seconds")
