import numpy as np
import pytest
from adb_auto_player.ocr import OEM, PSM, Lang, TesseractBackend, TesseractConfig
from PIL import Image, ImageDraw, ImageFont


class TestImageGenerator:
    """Helper class to generate test images with known text content."""

    @staticmethod
    def create_simple_text_image(
        text: str = "Hello World",
        size: tuple[int, int] = (400, 100),
        font_size: int = 24,
        background_color: str = "white",
        text_color: str = "black",
    ) -> np.ndarray:
        """Create a simple image with text."""
        img = Image.new("RGB", size, background_color)
        draw = ImageDraw.Draw(img)

        # Try to use a default font, fallback to basic if not available
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None

        # Calculate text position (centered)
        if font:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            # Rough estimation if no font available
            text_width = len(text) * 10
            text_height = 15

        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2

        draw.text((x, y), text, fill=text_color, font=font)

        # Convert PIL image to numpy array
        return np.array(img)

    @staticmethod
    def create_multi_line_image(
        lines: list[str],
        size: tuple[int, int] = (500, 300),
        font_size: int = 20,
        line_spacing: int = 10,
    ) -> np.ndarray:
        """Create an image with multiple lines of text."""
        img = Image.new("RGB", size, "white")
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None

        y_offset = 20
        for line in lines:
            draw.text((20, y_offset), line, fill="black", font=font)
            y_offset += font_size + line_spacing

        return np.array(img)

    @staticmethod
    def create_paragraph_image() -> np.ndarray:
        """Create an image with paragraph structure."""
        lines = [
            "This is the first paragraph.",
            "It contains multiple sentences.",
            "",
            "This is the second paragraph.",
            "It also has multiple sentences.",
            "And this is the third sentence.",
        ]
        return TestImageGenerator.create_multi_line_image(lines, size=(600, 400))

    @staticmethod
    def create_block_text_image() -> np.ndarray:
        """Create an image with distinct text blocks."""
        img = Image.new("RGB", (600, 400), "white")
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("arial.ttf", 18)
        except OSError:
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None

        # Block 1 - Top left
        draw.text(
            (20, 20), "Block One\nFirst line\nSecond line", fill="black", font=font
        )

        # Block 2 - Top right
        draw.text(
            (320, 20), "Block Two\nAnother line\nYet another", fill="black", font=font
        )

        # Block 3 - Bottom
        draw.text(
            (20, 200),
            "Block Three is at the bottom\nWith some more text",
            fill="black",
            font=font,
        )

        return np.array(img)


@pytest.fixture
def tesseract_backend():
    """Create a TesseractBackend instance for testing."""
    config = TesseractConfig(oem=OEM.DEFAULT, psm=PSM.DEFAULT, lang=Lang.ENGLISH)
    return TesseractBackend(config)


@pytest.fixture
def simple_text_image():
    """Create a simple test image with known text."""
    return TestImageGenerator.create_simple_text_image("Hello World")


@pytest.fixture
def multi_line_image():
    """Create a multi-line test image."""
    lines = ["First line", "Second line", "Third line"]
    return TestImageGenerator.create_multi_line_image(lines)


@pytest.fixture
def paragraph_image():
    """Create a paragraph test image."""
    return TestImageGenerator.create_paragraph_image()


@pytest.fixture
def block_text_image():
    """Create a block text test image."""
    return TestImageGenerator.create_block_text_image()
