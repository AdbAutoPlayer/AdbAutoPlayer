import cv2
import numpy as np


class Scaling:
    """Image scaling functions."""

    @staticmethod
    def scale_percent(img: np.ndarray, scale_percent: float) -> np.ndarray:
        """Scale image by a percentage (e.g. 1.8 means 180%)."""
        height, width = img.shape[:2]
        new_width = int(width * scale_percent)
        new_height = int(height * scale_percent)
        return cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
