"""Auto Player Vision Base Module."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar

from .models import Crop, Image, MatchMode, Preprocessing
from ..interaction.models import Coordinates

T = TypeVar("T")


class Vision(ABC, Generic[T]):
    """Vision abstract base class."""

    @abstractmethod
    def locate(
        self,
        input_screen_obj: Image[T],
        target_template_obj: Image[T],
        match_mode: MatchMode,
        confidence: float | None = None,
    ) -> Coordinates | None: ...

    @abstractmethod
    def locate_all(
        self,
        input_screen_obj: Image[T],
        target_template_obj: Image[T],
        min_distance: int,
        confidence: float | None = None,
    ) -> list[Coordinates] | None: ...

    @abstractmethod
    def locate_worst_match(
        self, input_screen_obj: Image[T], target_template_obj: Image[T]
    ) -> Coordinates | None: ...

    @abstractmethod
    def load_template_image(
        self, path: str | Path, preprocessing: Preprocessing | None = None
    ) -> Image[T]:
        """Loads an image from a file path and prepares it as a template.

        Args:
            path: The file path to the image.
            preprocessing: Optional preprocessing to apply to this template image.

        Returns:
            An Image[T] object representing the loaded template.
        """
        ...

    @abstractmethod
    def crop_image_data(
        self, image_data: T, crop_settings: Crop
    ) -> tuple[T, Coordinates]:
        """Crops the raw image data.

        Args:
            image_data: The raw image data (type T) to crop.
            crop_settings: The crop percentages (using the Crop NamedTuple).

        Returns:
            A tuple containing the cropped raw image data (type T)
            and the (x, y) offset of the crop relative to the original image_data.
        """
        ...
