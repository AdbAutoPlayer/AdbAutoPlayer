"""Auto Player Connection Base Module."""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic

from auto_player.connection.models import (
    ConnectionConfig,
    DeviceDetails,
    DeviceIdentifier,
    ForwardedPort,
)

T = TypeVar("T")


class Connection(Generic[T], ABC):
    """Abstract base class for device connections."""

    def __init__(self, config: ConnectionConfig) -> None:
        """Initializes the connection with a given configuration.

        Args:
            config: The configuration for the connection.
        """
        self._config = config
        self._device: T | None = None

    @property
    def config(self) -> ConnectionConfig:
        """The configuration for the connection."""
        return self._config

    @property
    def device(self) -> T | None:
        """The connected device instance, or None if not connected."""
        return self._device

    @device.setter
    def device(self, value: T | None) -> None:
        """Sets the device instance."""
        self._device = value

    @abstractmethod
    def connect(self, device_identifier: DeviceIdentifier | None = None) -> None:
        """Connects to a device.

        If device_identifier is None, attempts to connect to the first available
        or a default device.

        Args:
            device_identifier: The identifier of the device to connect to.
                               Can be None to connect to a default/first device.
        """
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnects from the currently connected device."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Checks if a device is currently connected and responsive.

        Returns:
            True if a device is connected and active, False otherwise.
        """
        ...

    @property
    @abstractmethod
    def device_serial(self) -> str | None:
        """The serial number of the connected device, if available.

        Returns:
            The device serial as a string, or None if not connected or not applicable.
        """
        ...

    @abstractmethod
    def list_available_devices(self) -> list[DeviceDetails]:
        """Lists all devices currently available to the connection endpoint.

        Returns:
            A list of DeviceDetails objects.
        """
        ...

    @abstractmethod
    def execute_shell_command(
        self, command: str, timeout: int | None = None
    ) -> str:
        """Executes a shell command on the connected device.

        Args:
            command: The command to execute.
            timeout: Optional timeout in seconds for the command execution.

        Returns:
            The output of the command as a string.
        """
        ...

    @abstractmethod
    def screencap(self) -> bytes:
        """Captures a screenshot of the connected device.

        Returns:
            The screenshot data as bytes.
        """
        ...

    @abstractmethod
    def push_file(self, source_path: str, destination_path: str) -> None:
        """Pushes a file from the local system to the connected device.

        Args:
            source_path: The path to the source file on the local system.
            destination_path: The path to the destination on the device.
        """
        ...

    @abstractmethod
    def pull_file(self, source_path: str, destination_path: str) -> None:
        """Pulls a file from the connected device to the local system.

        Args:
            source_path: The path to the source file on the device.
            destination_path: The path to the destination on the local system.
        """
        ...

    @abstractmethod
    def forward_port(
        self, local_port: int, remote_port: int | str, no_rebind: bool = False
    ) -> ForwardedPort:
        """Forwards a local port to a remote port on the device.

        Args:
            local_port: The local port number (e.g., 8080).
            remote_port: The remote port number or a string descriptor
                         (e.g., 8000 or "tcp:8000" or "localabstract:name").
            no_rebind: If True, an error is raised if the local port is already
                       forwarded. If False (default), the existing forward is
                       updated.

        Returns:
            A ForwardedPort object representing the established forward.
        """
        ...

    @abstractmethod
    def list_forwarded_ports(self) -> list[ForwardedPort]:
        """Lists all currently forwarded ports for the connected device.

        Returns:
            A list of ForwardedPort objects.
        """
        ...

    @abstractmethod
    def remove_forwarded_port(self, local_port: int) -> None:
        """Removes a port forwarding rule.

        Args:
            local_port: The local port of the forwarding rule to remove.
        """
        ...

    @abstractmethod
    def remove_all_forwarded_ports(self) -> None:
        """Removes all port forwarding rules for the connected device."""
        ...
