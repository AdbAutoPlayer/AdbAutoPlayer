"""Tesseract Config."""

from dataclasses import dataclass

from .tesseract_lang import Lang
from .tesseract_oem import OEM
from .tesseract_psm import PSM


@dataclass(frozen=True)
class TesseractConfig:
    """Tesseract Configuration."""

    oem: OEM = OEM.DEFAULT
    psm: PSM = PSM.DEFAULT
    lang: Lang = Lang.ENGLISH

    @property
    def lang_string(self) -> str:
        """Get language code as string."""
        return self.lang.value

    @property
    def config_string(self) -> str:
        """Get config string to be passed to tesseract binary."""
        return f"--oem {self.oem.value} --psm {self.psm.value}"
