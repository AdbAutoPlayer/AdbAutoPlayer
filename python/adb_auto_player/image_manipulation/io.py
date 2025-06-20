"""All IO related functions for images.

Provides functionality to load and cache images efficiently.

"""

from pathlib import Path

import cv2
import numpy as np

from .color import to_grayscale

template_cache: dict[str, np.ndarray] = {}


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

    cache_key = f"{image_path}_{image_scale_factor}_grayscale={grayscale}"
    if cache_key in template_cache:
        return template_cache[cache_key]

    image = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Failed to load image from path: {image_path}")

    if image_scale_factor != 1.0:
        new_width = int(image.shape[1] * image_scale_factor)
        new_height = int(image.shape[0] * image_scale_factor)
        image = cv2.resize(
            image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4
        )

    if grayscale:
        image = to_grayscale(image)

    template_cache[cache_key] = image
    return image
