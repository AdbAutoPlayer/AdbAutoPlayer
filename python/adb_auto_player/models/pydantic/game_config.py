"""Base configuration functionality for all game configs."""

import logging
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import cast

from pydantic import BaseModel
from pydantic.fields import FieldInfo


class GameConfig(BaseModel):
    """Base configuration class with shared functionality."""

    @classmethod
    @lru_cache(maxsize=1)
    def from_toml(cls, file_path: Path):
        """Create a Config instance from a TOML file.

        Args:
            file_path (Path): Path to the TOML file.

        Returns:
            An instance of the Config class initialized with data from the TOML file.
        """
        toml_data = {}
        if file_path.exists():
            try:
                with open(file_path, "rb") as f:
                    toml_data = tomllib.load(f)
            except Exception as e:
                logging.error(
                    f"Error reading config file: {e} - using default config values"
                )
        else:
            logging.debug("Using default config values")

        default_data = {}
        for field in cls.model_fields.values():
            field = cast(FieldInfo, field)
            if field.alias not in toml_data:
                field_type = field.annotation
                if hasattr(field_type, "model_fields"):
                    default_data[field.alias] = field_type().model_dump()

        merged_data = {**default_data, **toml_data}
        return cls(**merged_data)
