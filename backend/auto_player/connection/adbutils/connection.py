"""Auto Player Connection Through adbutils Module."""

import io
import logging
from typing import cast

import adbutils
from adbutils import AdbError, AdbTimeout
from adbutils._device import AdbDevice
from PIL import Image

from auto_player.connection.base import Connection
from auto_player.connection.models import (
    ConnectionConfig,
    DeviceDetails,
    DeviceIdentifier,
    DeviceState,
    ForwardedPort,
)
from auto_player.exception.exceptions import (
    DeviceCommandError,
    ConnectionError,
    DeviceNotFoundError,
)


class AdbUtilsConnection(Connection[AdbDevice]):
    """Manages ADB connections and operations using the adbutils library."""

    def __init__(self, config: ConnectionConfig) -> None:
        """Initializes the AdbUtilsConnection.

        Args:
            config: The connection configuration.
        """
        super().__init__(config)
        self._adb: adbutils.AdbClient | None = None
        self.logger = logging.getLogger(__name__)

    def _get_adb_client(self) -> adbutils.AdbClient:
        """Initializes and returns the AdbClient instance.

        Raises:
            ConnectionError: If the AdbClient cannot be initialized.

        Returns:
            The AdbClient instance.
        """
        if self._adb is None:
            try:
                self._adb = adbutils.AdbClient(
                    host=self.config.host, port=self.config.port
                )
            except AdbError as e:
                self.logger.error(f"Failed to initialize ADB client: {e}")
                raise ConnectionError(f"Failed to initialize ADB client: {e}") from e
        return self._adb

    def connect(self, device_identifier: DeviceIdentifier | None = None) -> None:
        """Connects to an ADB device.

        If device_identifier is None, it attempts to connect to the first
        available device. If multiple devices are available and no identifier
        is specified, a warning is logged, and the first device is used.

        Args:
            device_identifier: The identifier of the device to connect to.

        Raises:
            DeviceNotFoundError: If the specified device is not found or no
                                 devices are available.
            ConnectionError: If there's an issue connecting to the device.
        """
        adb = self._get_adb_client()
        target_serial: str | None = None

        if device_identifier:
            target_serial = str(device_identifier)
            self.logger.info(f"Attempting to connect to device: {target_serial}")
        else:
            self.logger.info("No device identifier specified, listing available devices.")
            try:
                devices = adb.device_list()
            except AdbError as e:
                self.logger.error(f"Failed to list ADB devices: {e}")
                raise ConnectionError(f"Failed to list ADB devices: {e}") from e

            if not devices:
                self.logger.warning("No ADB devices found.")
                raise DeviceNotFoundError("No ADB devices found.")
            if len(devices) > 1:
                self.logger.warning(
                    f"Multiple ADB devices found ({[d.serial for d in devices]}). "
                    f"Connecting to the first one: {devices[0].serial}."
                )
            target_serial = devices[0].serial
            self.logger.info(f"Attempting to connect to first available device: {target_serial}")

        if not target_serial:  # Should not happen if logic above is correct
            raise DeviceNotFoundError("Could not determine target device serial.")

        try:
            device = adb.device(serial=target_serial)
            if device is None:
                raise DeviceNotFoundError(f"Device {target_serial} not found by ADB client.")
            # Ensure the device is responsive by checking its state
            state = device.get_state()
            if state != "device":
                self.logger.error(f"Device {target_serial} is not in 'device' state (state: {state}). Cannot connect.")
                raise DeviceNotFoundError(f"Device {target_serial} is in state '{state}', not 'device'.")
            self.device = device
            self.logger.info(f"Successfully connected to device: {self.device_serial}")
        except AdbError as e:
            self.logger.error(f"Failed to connect to device {target_serial}: {e}")
            raise DeviceNotFoundError(f"Failed to connect to device {target_serial}: {e}") from e
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while connecting to {target_serial}: {e}")
            raise ConnectionError(f"An unexpected error occurred while connecting to {target_serial}: {e}") from e

    def disconnect(self) -> None:
        """Disconnects from the ADB device.

        For adbutils, there isn't an explicit 'disconnect' for a device object.
        Setting the internal device reference to None effectively disconnects it
        from the perspective of this class.
        """
        if self.device:
            self.logger.info(f"Disconnecting from device: {self.device_serial}")
            self.device = None
        else:
            self.logger.info("No device was connected.")

    def is_connected(self) -> bool:
        """Checks if a device is connected and responsive.

        Returns:
            True if a device is connected and responsive, False otherwise.
        """
        if not self.device:
            return False
        try:
            state = self.device.get_state()
            return state == "device"
        except AdbError:
            self.logger.warning(f"Device {self.device_serial} is not responsive.")
            return False

    @property
    def device_serial(self) -> str | None:
        """The serial number of the connected device.

        Returns:
            The device serial as a string, or None if not connected.
        """
        if self.device:
            return self.device.serial
        return None

    def list_available_devices(self) -> list[DeviceDetails]:
        """Lists all devices currently available to the ADB server.

        Returns:
            A list of DeviceDetails objects.

        Raises:
            ConnectionError: If there's an issue communicating with the ADB server.
        """
        adb = self._get_adb_client()
        try:
            adb_devices = adb.device_list()
            detailed_devices: list[DeviceDetails] = []
            for adb_dev in adb_devices:
                device_state: DeviceState
                try:
                    state_str = adb_dev.get_state()
                    if state_str is None:
                        self.logger.warning(f"Device state for {adb_dev.serial} is None. Defaulting to UNKNOWN.")
                        device_state = DeviceState.UNKNOWN
                    else:
                        device_state = DeviceState(state_str.lower())
                except ValueError:
                    self.logger.warning(f"Unknown device state value received for {adb_dev.serial}. Defaulting to UNKNOWN.")
                    device_state = DeviceState.UNKNOWN
                except AdbError as e:  # Catch error if get_state fails for a specific device
                    self.logger.warning(f"Error getting state for {adb_dev.serial}: {e}. Defaulting to UNKNOWN.")
                    device_state = DeviceState.UNKNOWN

                identifier = DeviceIdentifier(serial=adb_dev.serial)
                detailed_devices.append(
                    DeviceDetails(identifier=identifier, state=device_state)
                )
            return detailed_devices
        except AdbError as e:
            self.logger.error(f"Failed to list ADB devices: {e}")
            raise ConnectionError(f"Failed to list ADB devices: {e}") from e

    def execute_shell_command(
        self, command: str, timeout: int | None = None
    ) -> str:
        """Executes a shell command on the connected device.

        Args:
            command: The command to execute.
            timeout: Optional timeout in seconds.

        Returns:
            The output of the command as a string.

        Raises:
            ConnectionError: If no device is connected.
            DeviceCommandError: If the command fails or times out.
        """
        if not self.device:
            raise ConnectionError("No device connected to execute command.")
        try:
            self.logger.debug(f"Executing shell command: '{command}' with timeout: {timeout}")
            # adbutils shell(stream=False) is expected to return str
            # However, type hints might not be precise enough, so we cast.
            result = cast(str, self.device.shell(command, timeout=timeout, stream=False))
            return result
        except AdbTimeout as e:
            self.logger.error(f"Timeout executing command '{command}': {e}")
            raise DeviceCommandError(command, f"Timeout: {e}", str(e)) from e
        except AdbError as e:
            self.logger.error(f"Error executing command '{command}': {e}")
            raise DeviceCommandError(command, str(e), str(e)) from e

    def screencap(self) -> bytes:
        """Captures a screenshot of the connected device.

        Returns:
            The screenshot data as PNG bytes.

        Raises:
            ConnectionError: If no device is connected.
            DeviceCommandError: If the screenshot capture fails.
        """
        if not self.device:
            raise ConnectionError("No device connected to capture screenshot.")
        try:
            self.logger.debug("Capturing screenshot.")
            pil_image: Image.Image = self.device.screenshot()
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format="PNG")
            return img_byte_arr.getvalue()
        except AdbError as e:
            self.logger.error(f"Failed to capture screenshot: {e}")
            raise DeviceCommandError("screencap", str(e), str(e)) from e

    def push_file(self, source_path: str, destination_path: str) -> None:
        """Pushes a file to the device.

        Args:
            source_path: Path to the local source file.
            destination_path: Path to the remote destination on the device.

        Raises:
            ConnectionError: If no device is connected.
            DeviceCommandError: If the push operation fails.
        """
        if not self.device:
            raise ConnectionError("No device connected to push file.")
        try:
            self.logger.info(f"Pushing file from '{source_path}' to '{destination_path}'")
            self.device.sync.push(source_path, destination_path)
            self.logger.debug("File push successful.")
        except AdbError as e:
            self.logger.error(f"Failed to push file '{source_path}' to '{destination_path}': {e}")
            raise DeviceCommandError(f"push {source_path} {destination_path}", str(e), str(e)) from e

    def pull_file(self, source_path: str, destination_path: str) -> None:
        """Pulls a file from the device.

        Args:
            source_path: Path to the remote source file on the device.
            destination_path: Path to the local destination.

        Raises:
            ConnectionError: If no device is connected.
            DeviceCommandError: If the pull operation fails.
        """
        if not self.device:
            raise ConnectionError("No device connected to pull file.")
        try:
            self.logger.info(f"Pulling file from '{source_path}' to '{destination_path}'")
            self.device.sync.pull(source_path, destination_path)
            self.logger.debug("File pull successful.")
        except AdbError as e:
            self.logger.error(f"Failed to pull file '{source_path}' to '{destination_path}': {e}")
            raise DeviceCommandError(f"pull {source_path} {destination_path}", str(e), str(e)) from e

    def forward_port(
        self, local_port: int, remote_port: int | str, no_rebind: bool = False
    ) -> ForwardedPort:
        """Forwards a local port to a remote port on the device.

        Args:
            local_port: The local port number (e.g., 8080).
            remote_port: The remote port (e.g., 8000 or "tcp:8000" or "localabstract:name").
            no_rebind: If True, an error is raised if the local port is already forwarded.

        Returns:
            A ForwardedPort object representing the established forward.

        Raises:
            ConnectionError: If no device is connected.
            DeviceCommandError: If port forwarding fails or device serial is unavailable.
        """
        if not self.device:
            raise ConnectionError("No device connected to forward port.")

        local_spec = f"tcp:{local_port}"
        remote_spec = (
            f"tcp:{remote_port}" if isinstance(remote_port, int) else remote_port
        )

        try:
            self.logger.info(
                f"Forwarding port: local '{local_spec}' to remote '{remote_spec}' (norebind={no_rebind})"
            )
            self.device.forward(local_spec, remote_spec, norebind=no_rebind)

            current_device_serial = self.device_serial
            if not current_device_serial:
                # This should ideally not happen if self.device is set and responsive
                self.logger.error("Device serial not available after attempting to forward port.")
                raise DeviceCommandError("forward", "Device serial not available after forwarding.", None)
            return ForwardedPort(
                serial=current_device_serial, local=local_spec, remote=remote_spec
            )
        except AdbError as e:
            self.logger.error(f"Failed to forward port {local_spec} -> {remote_spec}: {e}")
            raise DeviceCommandError(f"forward {local_spec} {remote_spec}", str(e), str(e)) from e

    def list_forwarded_ports(self) -> list[ForwardedPort]:
        """Lists all currently forwarded ports for the connected device.

        Returns:
            A list of ForwardedPort objects.

        Raises:
            ConnectionError: If no device is connected.
            DeviceCommandError: If listing forwarded ports fails.
        """
        if not self.device:
            raise ConnectionError("No device connected to list forwarded ports.")
        try:
            self.logger.debug("Listing forwarded ports.")
            adb_forward_items = self.device.forward_list()
            return [
                ForwardedPort(
                    serial=item.serial, local=item.local, remote=item.remote
                )
                for item in adb_forward_items
            ]
        except AdbError as e:
            self.logger.error(f"Failed to list forwarded ports: {e}")
            raise DeviceCommandError("forward --list", str(e), str(e)) from e

    def remove_forwarded_port(self, local_port: int) -> None:
        """Removes a port forwarding rule by local port.

        Args:
            local_port: The local port of the forwarding rule to remove.

        Raises:
            ConnectionError: If no device is connected.
            DeviceCommandError: If removing the forwarded port fails.
        """
        if not self.device:
            raise ConnectionError("No device connected to remove forwarded port.")
        local_spec = f"tcp:{local_port}"
        try:
            self.logger.info(f"Removing forwarded port: {local_spec}")
            # self.device will be AdbDevice type
            removed = self.device.forward_remove(local_spec)  # type: ignore[attr-defined]
            if not removed:
                self.logger.warning(
                    f"Failed to remove port forward for local spec '{local_spec}' "
                    f"on device {self.device_serial}. The port may not have been forwarded."
                )
            self.logger.debug(f"Successfully removed forwarded port: {local_spec}")
        except AdbError as e:
            self.logger.error(f"Failed to remove forwarded port {local_spec}: {e}")
            raise DeviceCommandError(f"forward --remove {local_spec}", str(e), str(e)) from e

    def remove_all_forwarded_ports(self) -> None:
        """Removes all port forwarding rules for the connected device.

        Raises:
            ConnectionError: If no device is connected.
            DeviceCommandError: If removing all forwarded ports fails.
        """
        if not self.device:
            raise ConnectionError("No device connected to remove all forwarded ports.")
        try:
            self.logger.info("Removing all forwarded ports.")
            # self.device will be AdbDevice type
            removed_all = self.device.forward_remove_all()  # type: ignore[attr-defined]
            if not removed_all:
                self.logger.warning(
                    f"Failed to remove all port forwards on device {self.device_serial}. "
                    "Not all forwards may have been removed."
                )
            self.logger.debug("Successfully removed all forwarded ports.")
        except AdbError as e:
            self.logger.error(f"Failed to remove all forwarded ports: {e}")
            raise DeviceCommandError("forward --remove-all", str(e), str(e)) from e
