"""Base Settings functionality for all game Settings."""

import logging
import tomllib
from pathlib import Path
from typing import cast

from pydantic import BaseModel
from pydantic.fields import FieldInfo


class GameSettings(BaseModel):
    """Base Settings class with shared functionality."""

    @classmethod
    def from_toml(cls, file_path: Path):
        """Create a GameSettings instance from a TOML file.

        Args:
            file_path (Path): Path to the TOML file.

        Returns:
            An instance of GameSettings class initialized with data from the TOML file.
        """
        toml_data = {}
        if file_path.exists():
            try:
                with open(file_path, "rb") as f:
                    toml_data = tomllib.load(f)
            except Exception as e:
                logging.error(
                    f"Error reading Settings: {e} - using default GameSettings"
                )
        else:
            logging.debug("Using default GameSettings")

        default_data = {}
        for field in cls.model_fields.values():
            field = cast(FieldInfo, field)
            if field.alias not in toml_data:
                field_type = field.annotation
                if hasattr(field_type, "model_fields"):
                    default_data[field.alias] = field_type().model_dump()

        merged_data = {**default_data, **toml_data}
        return cls(**merged_data)
