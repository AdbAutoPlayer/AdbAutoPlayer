from typing import Annotated

from pydantic import BaseModel, Field

from .toml_settings import TomlSettings

# Type constraints
PortInt = Annotated[int, Field(ge=1024, le=65535)]
FPSInt = Annotated[int, Field(ge=1, le=60)]
NonNegativeInt = Annotated[int, Field(ge=0)]


class AdvancedSettings(BaseModel):
    """Advanced settings model."""

    adb_host: str = Field("127.0.0.1", title="ADB Host")
    adb_port: PortInt = Field(5037, title="ADB Port")
    hardware_decoding: bool = Field(False, title="Enable Hardware Decoding")
    auto_resolve_device: bool = Field(
        True,
        title="Automatically Select Available Device",
    )


class DeviceSettings(BaseModel):
    """ADB Device settings model."""

    id: str = Field("127.0.0.1:5555", title="Device ID")
    streaming: bool = Field(True, title="Real-time Display Streaming")
    streaming_fps: FPSInt = Field(30, title="Streaming FPS")
    use_wm_resize: bool = Field(False, title="Resize Display (Phone/Tablet)")


class AdbSettings(TomlSettings):
    """Adb settings model."""

    device: DeviceSettings = Field(default_factory=DeviceSettings, title="Device")
    advanced: AdvancedSettings = Field(
        default_factory=AdvancedSettings, title="Advanced"
    )
