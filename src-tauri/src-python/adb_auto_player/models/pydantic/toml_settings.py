import logging
import tomllib
from pathlib import Path

from pydantic import BaseModel


class TomlSettings(BaseModel):
    """Base Settings class with shared functionality."""

    @classmethod
    def from_toml(cls, file_path: Path):
        """Create a TomlSettings instance from a TOML file.

        Args:
            file_path (Path): Path to the TOML file.

        Returns:
            An instance of TomlSettings class initialized with data from the TOML file.
        """
        settings = cls()

        if not file_path.exists():
            logging.debug("Using default Settings")
            return settings

        try:
            with open(file_path, "rb") as f:
                toml_data = tomllib.load(f)

            settings = cls.model_validate(
                {**settings.model_dump(by_alias=True), **toml_data},
                extra="ignore",
                by_alias=True,
                by_name=True,
            )
        except Exception as e:
            logging.error(f"Error reading Settings: {e} - using default")

        return settings
