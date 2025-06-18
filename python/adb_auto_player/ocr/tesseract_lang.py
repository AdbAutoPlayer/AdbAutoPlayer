"""Tesseract Lang option."""

from enum import StrEnum


class Lang(StrEnum):
    """Tesseract Language code enumeration."""

    ENGLISH = "eng"

    @staticmethod
    def get_supported_languages() -> list[str]:
        """Return a list of supported languages."""
        return [lang.value for lang in Lang]
