import threading
import logging
import time
from PIL import Image
import queue
from adbutils import AdbDevice, AdbConnection

from av.codec.context import CodecContext


class DeviceStream:
    def __init__(self, device: AdbDevice, fps: int = 30, buffer_size: int = 2):
        """Initialize the screen stream.

        Args:
            device: AdbDevice instance
            fps: Target frames per second (default: 30)
            buffer_size: Number of frames to keep in buffer (default: 2)
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

    def _stream_screen(self):
        """Background thread that continuously captures frames."""
        buffer = b""

        while self._running:
            try:
                # Start screenrecord process
                cmd = f"screenrecord --output-format=h264 --time-limit=1 -"
                self._process = self.device.shell(cmd, stream=True)

                while self._running:
                    chunk = self._process.read(4096)
                    if not chunk:
                        break

                    buffer += chunk

                    # Try to decode as many frames as possible from the buffer
                    try:
                        packets = self.codec.parse(buffer)
                        for packet in packets:
                            frames = self.codec.decode(packet)
                            for frame in frames:
                                # Convert frame to PIL Image
                                image = Image.fromarray(
                                    frame.to_ndarray(format="rgb24")
                                )

                                # Update queue
                                if self.frame_queue.full():
                                    # Remove oldest frame if queue is full
                                    try:
                                        self.frame_queue.get_nowait()
                                    except queue.Empty:
                                        pass
                                self.frame_queue.put(image)

                        # Keep any remaining partial data in the buffer
                        buffer = b""

                    except Exception:
                        # If decoding fails, keep the buffer and continue
                        if len(buffer) > 1024 * 1024:
                            # Prevent buffer from growing too large
                            buffer = buffer[-1024 * 1024 :]
                        continue

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
