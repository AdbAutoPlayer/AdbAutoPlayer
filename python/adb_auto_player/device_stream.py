"""ADB Auto Player Device Stream Module."""

import logging
import platform
import queue
import threading
import time

from adbutils import AdbConnection, AdbDevice
from av.codec.context import CodecContext
from PIL import Image


class StreamingNotSupportedError(Exception):
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
        self.latest_frame: Image.Image | None = None
        self._running = False
        self._stream_thread: threading.Thread | None = None
        self._process: AdbConnection | None = None
        self.codec: CodecContext = CodecContext.create("h264", "r")
        self.is_arm_mac = (
            platform.system() == "Darwin"
            and platform.machine().startswith(("arm", "aarch"))
        )

        if self.is_arm_mac:
            raise StreamingNotSupportedError(
                "Device Stream is not implemented for macOS"
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
            self._process.close()
            self._process = None
        if self._stream_thread:
            self._stream_thread.join()
            self._stream_thread = None

        # Clear the queue
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break

    def get_latest_frame(self) -> Image.Image | None:
        """Get the most recent frame from the stream."""
        try:
            while not self.frame_queue.empty():
                self.latest_frame = self.frame_queue.get_nowait()
        except queue.Empty:
            pass

        return self.latest_frame

    def _handle_stream_arm_mac(self) -> None:
        """Stream handler for Mac."""
        # TODO
        # h264 returns segmentation fault
        # raw-frames lags bluestacks to death
        # example command:
        # adb -s 127.0.0.1:5555 shell screenrecord --output-format=raw-frames
        # --time-limit=1 - | ffmpeg -f rawvideo -pix_fmt rgb24 -s 1080x1920 -i -
        # -f image2 -vcodec png frame%04d.png
        # maybe we can just brew install scrcpy and try with that?
        logging.error("Device Stream is not implemented for macOS")
        self.stop()

    def _handle_stream_windows(self) -> None:
        """Stream handler for Windows."""
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
                        image = Image.fromarray(frame.to_ndarray(format="rgb24"))

                        if self.frame_queue.full():
                            try:
                                self.frame_queue.get_nowait()
                            except queue.Empty:
                                pass
                        self.frame_queue.put(image)

                buffer = b""

            except Exception:
                if len(buffer) > 1024 * 1024:
                    buffer = buffer[-1024 * 1024 :]
                continue

    def _stream_screen(self) -> None:
        """Background thread that continuously captures frames."""
        while self._running:
            try:
                if self.is_arm_mac:
                    self._handle_stream_arm_mac()
                else:
                    self._handle_stream_windows()
            except Exception as e:
                if "was aborted by the software in your host machine" not in str(e):
                    logging.error(f"Stream error: {e}")
                time.sleep(1)
            finally:
                if self._process:
                    self._process.close()
                    self._process = None
