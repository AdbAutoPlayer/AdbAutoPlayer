import logging
from typing import Optional, Tuple, NoReturn, Union

from PIL import Image
import io
import cv2
import numpy as np

from adbutils._device import AdbDevice


def find_center(
    device: AdbDevice, template_image_path: str
) -> Optional[Tuple[int, int]]:
    return __find_template_center(
        base_image=get_screenshot(device),
        template_image=__load_image(image_path=template_image_path),
    )


def get_screenshot(device: AdbDevice) -> Union[Image.Image, NoReturn]:
    screenshot_data = device.shell("screencap -p", encoding=None)
    if isinstance(screenshot_data, bytes):
        return Image.open(io.BytesIO(screenshot_data))

    logging.critical(f"Screenshots cannot be recorded from device: {device.serial}")


def __find_template_center(
    base_image: Image.Image, template_image: Image.Image, threshold: float = 0.9
) -> Optional[Tuple[int, int]]:
    base_cv = cv2.cvtColor(np.array(base_image), cv2.COLOR_RGB2BGR)
    template_cv = cv2.cvtColor(np.array(template_image), cv2.COLOR_RGB2BGR)

    result = cv2.matchTemplate(base_cv, template_cv, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        # Get the center of the matched area
        template_height, template_width = template_cv.shape[:2]
        center_x = max_loc[0] + template_width // 2
        center_y = max_loc[1] + template_height // 2
        return center_x, center_y

    return None


def __load_image(image_path: str) -> Union[Image.Image, NoReturn]:
    try:
        image = Image.open(image_path)
        image.load()
        return image
    except FileNotFoundError:
        logging.critical(f"The file '{image_path}' does not exist.")
    except IOError:
        logging.critical(f"The file '{image_path}' is not a valid image.")
