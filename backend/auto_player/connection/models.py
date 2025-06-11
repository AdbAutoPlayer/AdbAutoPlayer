"""Auto Player Connection Models."""
from enum import Enum
from pydantic import BaseModel


class DeviceState(Enum):
    """Represents the state of an ADB device."""

    ONLINE = "device"  # Device is connected and ready
    OFFLINE = "offline"  # Device is not connected or not responding
    UNAUTHORIZED = "unauthorized"  # Device is connected but not authorized for debugging
    UNKNOWN = "unknown"  # Device state cannot be determined


class DeviceIdentifier(BaseModel):
    """Identifies a device, typically by serial or network address."""

    serial: str | None = None
    host: str | None = None
    port: int | None = None

    def model_post_init(self, __context: dict) -> None:
        if not self.serial and not (self.host and self.port):
            raise ValueError("Either serial or host and port must be provided.")

    def __str__(self) -> str:
        """Return a string representation of the identifier."""
        if self.serial:
            return self.serial
        if self.host and self.port:
            return f"{self.host}:{self.port}"
        # This case should ideally be prevented by model_post_init,
        # but as a fallback:
        return "invalid_identifier"


class DeviceDetails(BaseModel):
    """Holds detailed information about a connected device."""

    identifier: DeviceIdentifier
    state: DeviceState


class ForwardedPort(BaseModel):
    """Represents a forwarded port mapping."""

    serial: str  # The serial of the device the port is forwarded for
    local: str  # e.g., "tcp:6100"
    remote: str  # e.g., "tcp:7100"


class ConnectionConfig(BaseModel):
    """Configuration for establishing a connection to a device server."""

    host: str = "127.0.0.1"
    port: int
