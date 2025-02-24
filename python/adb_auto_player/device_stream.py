import threading
import logging
import time
import platform
from PIL import Image
import queue
from adbutils import AdbDevice, AdbConnection
from io import BytesIO
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
            return "screenrecord --output-format=png --bugreport -"
        else:
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
        """Get the most recent frame from the stream."""
        try:
            while not self.frame_queue.empty():
                self.latest_frame = self.frame_queue.get_nowait()
        except queue.Empty:
            pass

        return self.latest_frame

    def _process_png_frame(self, data: bytes) -> None:
        """Process PNG frame data directly in memory."""
        try:
            if not data:
                return

            # Process image directly from bytes
            image = Image.open(BytesIO(data))

            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
            self.frame_queue.put(image)

        except Exception as e:
            logging.error(f"Error processing PNG frame: {e}")

    def _process_h264(self, buffer: bytes) -> bytes:
        """Process H264 encoded frames."""
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
            return b""
        except Exception as e:
            logging.error(f"Error processing H264: {e}")
            if len(buffer) > 1024 * 1024:
                return buffer[-1024 * 1024 :]
            return buffer

    def _stream_screen(self):
        """Background thread that continuously captures frames."""
        buffer = b""
        png_header = b"\x89PNG\r\n\x1a\n"
        png_end = b"IEND\xaeB`\x82"

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

                        # Find and process complete PNG frames
                        while True:
                            start = buffer.find(png_header)
                            if start == -1:
                                break

                            end = buffer.find(png_end, start)
                            if end == -1:
                                break

                            # Process complete PNG frame (include the PNG end marker)
                            frame_data = buffer[start : end + len(png_end)]
                            self._process_png_frame(frame_data)
                            buffer = buffer[end + len(png_end) :]

                        # Prevent buffer from growing too large
                        if len(buffer) > 1024 * 1024:
                            buffer = buffer[-1024 * 1024 :]
                    else:
                        buffer += chunk
                        buffer = self._process_h264(buffer)

            except Exception as e:
                logging.error(f"Stream error: {e}")
                time.sleep(1)
                buffer = b""

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
