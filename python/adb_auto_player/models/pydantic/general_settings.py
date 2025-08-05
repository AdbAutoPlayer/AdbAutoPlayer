import logging
import tomllib
from pathlib import Path
from typing import Annotated, Literal, cast

from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo

# really just don't touch anything here, if the alias is not the same that the GO
# side uses it will break the settings

# Type constraints
PortInt = Annotated[int, Field(ge=1024, le=65535)]
FPSInt = Annotated[int, Field(ge=1, le=60)]
NonNegativeInt = Annotated[int, Field(ge=0)]


class AdvancedSettings(BaseModel):
    """Advanced settings model."""

    adb_host: str = Field("127.0.0.1", alias="host")
    adb_port: PortInt = Field(5037, alias="port")
    auto_player_host: str = Field("127.0.0.1", alias="auto_player_host")
    auto_player_port: PortInt = Field(62121, alias="auto_player_port")
    streaming_fps: FPSInt = Field(30, alias="streaming_fps")


class DeviceSettings(BaseModel):
    """ADB Device settings model."""

    id: str = Field("127.0.0.1:7555", alias="ID")
    streaming: bool = Field(True, alias="streaming")
    hardware_decoding: bool = Field(False, alias="hardware_decoding")
    use_wm_resize: bool = Field(False, alias="wm_size")


class LoggingSettings(BaseModel):
    """Logging settings model."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "FATAL"] = Field("INFO")
    debug_save_screenshots: NonNegativeInt = Field(60)
    action_log_limit: NonNegativeInt = Field(5)


class GeneralSettings(BaseModel):
    """General settings model."""

    advanced: AdvancedSettings = Field(..., alias="advanced")
    device: DeviceSettings = Field(..., alias="device")
    logging: LoggingSettings = Field(..., alias="logging")

    @classmethod
    def from_toml(cls, file_path: Path) -> "GeneralSettings":
        """Create GeneralSettings from a TOML file.

        Args:
            file_path (Path): Path to the TOML file.

        Returns:
            GeneralSettings
        """
        toml_data = {}
        if file_path.exists():
            try:
                with open(file_path, "rb") as f:
                    toml_data = tomllib.load(f)
            except Exception as e:
                logging.error(
                    f"Error reading General Settings file: {e} - using default values"
                )
        else:
            logging.debug("Using default General Settings values")

        default_data = {}
        for field in cls.model_fields.values():
            field = cast(FieldInfo, field)
            if field.alias not in toml_data:
                field_type = field.annotation
                if hasattr(field_type, "model_fields"):
                    default_data[field.alias] = field_type().model_dump()

        merged_data = {**default_data, **toml_data}
        return cls(**merged_data)
