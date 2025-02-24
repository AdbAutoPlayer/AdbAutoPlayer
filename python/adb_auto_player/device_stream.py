import threading
import logging
import time
import platform
from PIL import Image
import queue
from adbutils import AdbDevice, AdbConnection

from av.codec.context import CodecContext

import adb_auto_player.adb


class DeviceStream:
    def __init__(self, device: AdbDevice, fps: int = 30, buffer_size: int = 2):
        """Initialize the screen stream.

        Args:
            device: AdbDevice instance
            fps: Target frames per second (default: 30)
            buffer_size: Number of frames to keep in buffer (default: 2)
        """
        resolution = adb_auto_player.adb.get_screen_resolution(device)
        self.width, self.height = map(int, resolution.split("x"))
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

    def _get_screenrecord_command(self) -> str:
        """Get platform-specific screenrecord command."""
        if self.is_arm_mac:
            # Use more compatible options for ARM Macs
            return "screenrecord --bit-rate=8000000 --output-format=raw-frames -"
        else:
            # Original command for other platforms
            return "screenrecord --output-format=h264 --time-limit=1 -"

    def start(self):
        """Start the screen streaming thread."""
        if self._running:
            return

        self._running = True
        self._stream_thread = threading.Thread(target=self._stream_screen)
        self._stream_thread.daemon = True
        self._stream_thread.start()

    def stop(self):
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
        """Get the most recent frame from the stream.

        Returns:
            PIL.Image if available, None otherwise
        """
        try:
            # Try to get the newest frame without blocking
            while not self.frame_queue.empty():
                self.latest_frame = self.frame_queue.get_nowait()
        except queue.Empty:
            pass

        return self.latest_frame

    def _process_raw_frames(self, chunk: bytes) -> None:
        """Process raw frames format (for ARM Mac)."""
        try:
            bytes_per_pixel = 3  # RGB
            frame_size = self.width * self.height * bytes_per_pixel

            while len(chunk) >= frame_size:
                frame_data = chunk[:frame_size]
                chunk = chunk[frame_size:]

                image = Image.frombytes("RGB", (self.width, self.height), frame_data)

                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                self.frame_queue.put(image)

        except Exception as e:
            logging.error(f"Error processing raw frames: {e}")

    def _process_h264(self, buffer: bytes) -> bytes:
        """Process H264 encoded frames."""
        try:
            packets = self.codec.parse(buffer)
            for packet in packets:
                frames = self.codec.decode(packet)
                for frame in frames:
                    # Convert frame to PIL Image
                    image = Image.fromarray(frame.to_ndarray(format="rgb24"))

                    # Update queue
                    if self.frame_queue.full():
                        try:
                            self.frame_queue.get_nowait()
                        except queue.Empty:
                            pass
                    self.frame_queue.put(image)
            return b""  # Clear buffer after successful processing
        except Exception as e:
            logging.error(f"Error processing H264: {e}")
            if len(buffer) > 1024 * 1024:
                return buffer[-1024 * 1024 :]  # Keep last MB if buffer too large
            return buffer

    def _stream_screen(self):
        """Background thread that continuously captures frames."""
        buffer = b""

        while self._running:
            try:
                cmd = self._get_screenrecord_command()
                self._process = self.device.shell(cmd, stream=True)

                while self._running:
                    chunk = self._process.read(4096)
                    if not chunk:
                        break

                    if self.is_arm_mac:
                        buffer += chunk
                        self._process_raw_frames(buffer)
                    else:
                        buffer += chunk
                        buffer = self._process_h264(buffer)

            except Exception as e:
                logging.error(f"Stream error: {e}")
                time.sleep(1)  # Wait before retrying
                buffer = b""  # Clear buffer on error

            finally:
                if self._process:
                    self._process.close()
                    self._process = None

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
