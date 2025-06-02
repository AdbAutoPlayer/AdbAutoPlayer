"""ADB Auto Player Device Stream Module."""

import logging
import platform
import queue
import threading
import time

import cv2
import numpy as np
from adbutils import AdbConnection, AdbDevice
from av.codec.context import CodecContext

from .exceptions import AutoPlayerWarningError


class StreamingNotSupportedError(AutoPlayerWarningError):
    """Streaming is not yet implemented for the specified platform."""

    pass


class DeviceStream:
    """Device screen streaming."""

    def __init__(self, device: AdbDevice, fps: int = 30, buffer_size: int = 2):
        """Initialize the screen stream.

        Args:
            device: AdbDevice instance
            fps: Target frames per second (default: 30)
            buffer_size: Number of frames to keep in buffer (default: 2)

        Raises:
            StreamingNotSupportedError
        """
        self.device = device
        self.fps = fps
        self.buffer_size = buffer_size
        self.frame_queue: queue.Queue = queue.Queue(maxsize=buffer_size)
        self.latest_frame: np.ndarray | None = None
        self._running = False
        self._stream_thread: threading.Thread | None = None
        self._process: AdbConnection | None = None
        self.codec: CodecContext = CodecContext.create("h264", "r")
        is_arm_mac = platform.system() == "Darwin" and platform.machine().startswith(
            ("arm", "aarch")
        )

        if is_arm_mac and _device_is_emulator(device):
            raise StreamingNotSupportedError(
                "Emulators running on macOS do not support Device Streaming "
                "you can try using your Phone."
            )

    def start(self) -> None:
        """Start the screen streaming thread."""
        if self._running:
            return

        self._running = True
        self._stream_thread = threading.Thread(target=self._stream_screen)
        self._stream_thread.daemon = True
        self._stream_thread.start()

    def stop(self) -> None:
        """Stop the screen streaming thread."""
        self._running = False
        if self._process:
            try:
                self._process.close()
                self._process = None
            except AttributeError as e:
                if "'NoneType' object has no attribute 'close'" in str(e):
                    return
                raise
        if self._stream_thread:
            self._stream_thread.join()
            self._stream_thread = None

        # Clear the queue
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break

    def get_latest_frame(self) -> np.ndarray | None:
        """Get the most recent frame from the stream."""
        try:
            while not self.frame_queue.empty():
                self.latest_frame = self.frame_queue.get_nowait()
        except queue.Empty:
            pass

        return self.latest_frame

    def _handle_stream(self) -> None:
        """Generic stream handler."""
        self._process = self.device.shell(
            cmdargs="screenrecord --output-format=h264 --time-limit=1 -",
            stream=True,
        )

        buffer = b""
        while self._running:
            if self._process is None:
                break
            chunk = self._process.read(4096)
            if not chunk:
                break

            buffer += chunk

            # Try to decode frames from the buffer
            try:
                packets = self.codec.parse(buffer)
                for packet in packets:
                    frames = self.codec.decode(packet)
                    for frame in frames:
                        ndarray = frame.to_ndarray(format="rgb24")
                        bgr_frame = cv2.cvtColor(ndarray, cv2.COLOR_RGB2BGR)
                        if self.frame_queue.full():
                            try:
                                self.frame_queue.get_nowait()
                            except queue.Empty:
                                pass
                        self.frame_queue.put(bgr_frame)

                buffer = b""

            except Exception:
                if len(buffer) > 1024 * 1024:
                    buffer = buffer[-1024 * 1024 :]
                continue

    def _stream_screen(self) -> None:
        """Background thread that continuously captures frames."""
        while self._running:
            try:
                self._handle_stream()
            except Exception as e:
                if self._running:
                    if "was aborted by the software in your host machine" not in str(e):
                        logging.debug(f"Stream error: {e}")
                time.sleep(1)
            finally:
                if self._process:
                    try:
                        self._process.close()
                        self._process = None
                    except AttributeError as e:
                        if "'NoneType' object has no attribute 'close'" in str(e):
                            return
                        raise


def _device_is_emulator(device: AdbDevice) -> bool:
    """Checks if the device is an emulator."""
    result = str(device.shell('getprop | grep "Build"'))
    if "Build" in result:
        logging.debug('getprop contains "Build" assuming Emulator')
        return True
    logging.debug('getprop does not contain "Build" assuming Phone')
    return False
