"""All IO related functions for images.

Provides functionality to load and cache images efficiently.

"""

from pathlib import Path

import cv2
import numpy as np

from .color import Color

template_cache: dict[str, np.ndarray] = {}


class IO:
    """IO related operations."""

    @staticmethod
    def load_image(
        image_path: Path,
        image_scale_factor: float = 1.0,
        grayscale: bool = False,
    ) -> np.ndarray:
        """Loads an image from disk or returns the cached version if available.

        Resizes the image if needed and stores it in the global template_cache.

        Args:
            image_path: Path to the template image.
                Defaults to .png if no file_extension is specified.
            image_scale_factor: Scale factor for resizing the image.
            grayscale: Whether to convert the image to grayscale.

        Returns:
            np.ndarray
        """
        if image_path.suffix == "":
            image_path = image_path.with_suffix(".png")

        cache_key = f"{image_path}_{image_scale_factor}_grayscale={int(grayscale)}"
        if cache_key in template_cache:
            return template_cache[cache_key]

        image: np.ndarray = cv2.imdecode(
            np.fromfile(image_path, dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )

        if image is None:
            raise FileNotFoundError(f"Failed to load image from path: {image_path}")

        if image_scale_factor != 1.0:
            new_width = int(image.shape[1] * image_scale_factor)
            new_height = int(image.shape[0] * image_scale_factor)
            image = cv2.resize(
                image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4
            )

        if grayscale:
            image = Color.to_grayscale(image)

        template_cache[cache_key] = image
        return image.copy()

    @staticmethod
    def get_bgr_np_array_from_png_bytes(image_data: bytes) -> np.ndarray:
        """Converts bytes to numpy array.

        Raises:
            OSError
            ValueError
        """
        png_start_index = image_data.find(b"\x89PNG\r\n\x1a\n")
        # Slice the screenshot data to remove the warning
        # and keep only the PNG image data
        if png_start_index != -1:
            image_data = image_data[png_start_index:]

        np_data = np.frombuffer(image_data, dtype=np.uint8)
        img = cv2.imdecode(np_data, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode screenshot image data")
        return img

    @staticmethod
    def clear_cache() -> None:
        """Clears the template_cache dictionary."""
        template_cache.clear()
