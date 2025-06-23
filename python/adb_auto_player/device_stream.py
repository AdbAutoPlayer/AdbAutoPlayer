"""ADB Auto Player Device Stream Module."""

import logging
import platform
import threading
import time
from functools import lru_cache

import av
import numpy as np
from adb_auto_player.exceptions import AutoPlayerWarningError
from adb_auto_player.util import ConfigLoader
from adbutils import AdbConnection, AdbDevice
from av.codec.codec import UnknownCodecError
from av.codec.context import CodecContext


@lru_cache(maxsize=1)
def _get_best_decoder(hardware_decoding: bool) -> str:
    """Find and cache the best available H264 decoder."""
    selected_decoder = None

    if hardware_decoding:
        h264_decoders = _get_available_h264_decoders()

        for decoder in h264_decoders:
            try:
                _ = CodecContext.create(decoder, "r")
                selected_decoder = decoder
                break
            except UnknownCodecError:
                continue

    # explicitly try software h264 decoder
    if not selected_decoder:
        try:
            _ = CodecContext.create("h264", "r")
            selected_decoder = "h264"
        except UnknownCodecError:
            pass

    if hardware_decoding and selected_decoder == "h264":
        logging.warning(
            "Failed to initialise h264 hardware decoder, using software decoding"
        )

    if selected_decoder:
        logging.debug(f"Selected H264 decoder: {selected_decoder}")
        return selected_decoder

    raise StreamingNotSupportedError(
        "No h264 decoders available cannot handle Device Streaming."
    )


def _get_codec_context() -> CodecContext:
    """Get codec context using cached decoder selection."""
    hardware_decoding = (
        ConfigLoader().main_config.get("device", {}).get("hardware_decoding", False)
    )

    decoder_name = _get_best_decoder(hardware_decoding)
    return CodecContext.create(decoder_name, "r")


class StreamingNotSupportedError(AutoPlayerWarningError):
    """Streaming is not yet implemented for the specified platform."""

    pass


class DeviceStream:
    """Device screen streaming."""

    def __init__(self, device: AdbDevice, fps: int = 30):
        """Initialize the screen stream.

        Args:
            device: AdbDevice instance
            fps: Target frames per second (default: 30)

        Raises:
            StreamingNotSupportedError
        """
        is_arm_mac = platform.system() == "Darwin" and platform.machine().startswith(
            ("arm", "aarch")
        )
        if is_arm_mac and _device_is_emulator(device):
            raise StreamingNotSupportedError(
                "Emulators running on macOS do not support Device Streaming "
                "you can try using your Phone."
            )

        self.codec = _get_codec_context()
        self.device = device
        self.fps = fps
        self.latest_frame: np.ndarray | None = None
        self._frame_lock = threading.Lock()
        self._running = False
        self._stream_thread: threading.Thread | None = None
        self._process: AdbConnection | None = None

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

        # Clear the latest frame
        with self._frame_lock:
            self.latest_frame = None

    def get_latest_frame(self) -> np.ndarray | None:
        """Get the most recent frame from the stream."""
        with self._frame_lock:
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
                        with self._frame_lock:
                            self.latest_frame = ndarray

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


def _get_available_h264_decoders():
    """Returns a list of available H264 decoders."""
    known_decoders = [
        "h264_cuvid",  # NVIDIA GPU (high priority hardware decoder)
        "h264_qsv",  # Intel Quick Sync (hardware)
        "h264_vaapi",  # Intel/AMD VAAPI (hardware)
        "h264_v4l2m2m",  # ARM/Linux hardware decoder
        "h264",  # Software fallback decoder
    ]
    available = av.codecs_available
    return [decoder for decoder in known_decoders if decoder in available]
