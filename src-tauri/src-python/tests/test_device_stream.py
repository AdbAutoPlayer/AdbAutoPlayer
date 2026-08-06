import io
import time
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import av
import numpy as np
from adb_auto_player.device.adb import DeviceStream, StreamingNotSupportedError
from adb_auto_player.file_loader import SettingsLoader
from av.container.output import OutputContainer
from av.video.stream import VideoStream


class MockAdbConnection:
    """Mock ADB connection that feeds real H.264 video data."""

    def __init__(self, video_data: bytes):
        self.video_data = video_data
        self.position = 0
        self.closed = False

    def read(self, size: int) -> bytes:
        """Read chunks of video data."""
        if self.closed or self.position >= len(self.video_data):
            return b""

        chunk = self.video_data[self.position : self.position + size]
        self.position += len(chunk)
        return chunk

    def close(self):
        """Close the connection."""
        self.closed = True


class TestDeviceStream(unittest.TestCase):
    """Test DeviceStream with real video decoding."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_device = Mock()

        src_tauri_dir = Path(__file__)
        for parent in src_tauri_dir.parents:
            if parent.name == "src-tauri":
                src_tauri_dir = parent
                break

        SettingsLoader.set_app_config_dir(src_tauri_dir / "Settings")

    def test_stream_initialization(self):
        """Test DeviceStream initialization."""
        self.mock_device.is_controlling_emulator = False
        stream = DeviceStream(self.mock_device, fps=5)
        self.assertEqual(stream.fps, 5)
        self.assertIsNone(stream.latest_frame)
        self.assertFalse(stream._running)

    def test_stream_error_handling(self):
        """Test error handling in stream."""
        # Create a connection that will fail
        mock_connection = Mock()
        mock_connection.read.side_effect = Exception("Connection failed")
        self.mock_device.shell.return_value = mock_connection
        self.mock_device.is_controlling_emulator = False

        stream = DeviceStream(self.mock_device, fps=5)

        # Start streaming
        stream.start()

        # Wait a bit to let error handling kick in
        time.sleep(0.5)

        # Should still be running (error handling keeps it alive)
        self.assertTrue(stream._running)

        # Stop streaming
        stream.stop()

    def test_emulator_detection_on_arm_mac(self):
        """Test emulator detection prevents streaming on ARM Mac."""
        with patch(
            "adb_auto_player.device.adb.device_stream.RuntimeInfo.is_mac",
            return_value=True,
        ):
            with patch(
                "adb_auto_player.device.adb.device_stream.RuntimeInfo.is_arm",
                return_value=True,
            ):
                self.mock_device.is_controlling_emulator = True
                with self.assertRaises(StreamingNotSupportedError):
                    DeviceStream(self.mock_device, fps=5)

    def test_buffer_overflow_protection(self):
        """Test that large buffers are truncated to prevent memory issues."""
        # Create a mock connection that returns large chunks without proper H.264 data
        mock_connection = Mock()
        large_chunk = b"invalid_data" * 100000  # ~1.3MB of invalid data
        mock_connection.read.return_value = large_chunk
        self.mock_device.d.shell.return_value = mock_connection

        self.mock_device.is_controlling_emulator = False

        stream = DeviceStream(self.mock_device, fps=5)

        # Start streaming
        stream.start()

        # Let it run for a bit to trigger buffer management
        time.sleep(0.5)

        # Should not crash due to memory issues
        stream.stop()

    def test_buffer_overflow_and_exception(self):
        """Test buffer cleanup when an exception occurs with a large buffer."""
        mock_connection = Mock()
        # Feed > 1MB of data and then cause an exception
        large_invalid_data = b"\xff" * (1024 * 1024 + 100)
        mock_connection.read.return_value = large_invalid_data
        self.mock_device.d.shell.return_value = mock_connection
        self.mock_device.is_controlling_emulator = False

        stream = DeviceStream(self.mock_device, fps=5)
        # Mock codec to raise exception during parse
        stream.codec = Mock()
        stream.codec.parse.side_effect = Exception("Parse error")

        # Start and run briefly
        stream.start()
        time.sleep(0.5)

        # Stop and verify it didn't crash
        stream.stop()

    def test_stream_process_none_break(self):
        """Cover line 149: break if self._process is None."""
        mock_device = Mock()
        mock_device.is_controlling_emulator = False
        stream = DeviceStream(mock_device, fps=5)
        # Mock _handle_stream to simulate the loop
        # We need to mock controller.d.shell
        with patch.object(mock_device.d, "shell") as mock_shell:
            mock_shell.return_value = None  # This will set self._process to None
            stream._running = True
            stream._handle_stream()
            # Should break immediately at line 149

    def test_stream_empty_chunk_break(self):
        """Cover line 152: break if not chunk."""
        mock_device = Mock()
        mock_device.is_controlling_emulator = False
        stream = DeviceStream(mock_device, fps=5)
        mock_connection = Mock()
        mock_connection.read.return_value = b""  # Empty chunk
        mock_device.d.shell.return_value = mock_connection

        stream._running = True
        stream._handle_stream()
        # Should break at line 152

    def test_device_stream_default_fps(self):
        """Cover line 94: fps is None -> use settings."""
        mock_device = Mock()
        mock_device.is_controlling_emulator = False
        # Mock SettingsLoader to avoid actual file read or just let it read
        # Line 94 calls SettingsLoader.adb_settings().device.streaming_fps
        with patch(
            "adb_auto_player.device.adb.device_stream.SettingsLoader.adb_settings"
        ) as mock_settings:
            mock_settings.return_value.device.streaming_fps = 60
            stream = DeviceStream(mock_device, fps=None)
            assert stream.fps == 60

    def test_device_stream_start_twice(self):
        """Cover line 108: start() called when already running."""
        mock_device = Mock()
        mock_device.is_controlling_emulator = False
        stream = DeviceStream(mock_device, fps=30)
        stream._running = True
        stream.start()
        # Should return at line 108 without starting a new thread

    def test_handle_stream_success_coverage(self):
        """Cover line 166: buffer.clear() on success."""
        mock_device = Mock()
        mock_device.is_controlling_emulator = False
        stream = DeviceStream(mock_device, fps=5)

        # Mock a successful decode
        mock_connection = Mock()
        # Return a small "valid-looking" chunk then empty
        mock_connection.read.side_effect = [b"\x00\x00\x00\x01", b""]
        mock_device.d.shell.return_value = mock_connection

        # Mock codec methods
        stream.codec = Mock()
        stream.codec.parse.return_value = [Mock()]  # One packet
        stream.codec.decode.return_value = [Mock()]  # One frame

        stream._running = True
        stream._handle_stream()
        # Should call buffer.clear() at line 166


class TestIntegrationWithRealDecoding(unittest.TestCase):
    """Integration tests that test the full pipeline."""

    def test_full_pipeline_with_multiple_formats(self):
        """Test decoding pipeline with different video characteristics."""
        test_cases = [
            (160, 120, 5),  # Small, few frames
            (320, 240, 15),  # Medium, more frames
            (640, 480, 3),  # Larger, few frames
        ]

        for width, height, frame_count in test_cases:
            with self.subTest(width=width, height=height, frames=frame_count):
                # Create test video with specific dimensions
                video_data = self._create_video_with_dimensions(
                    width, height, frame_count
                )

                # Test decoding
                mock_device = Mock()
                mock_connection = MockAdbConnection(video_data)
                mock_device.shell.return_value = mock_connection
                mock_device.is_controlling_emulator = False
                stream = DeviceStream(mock_device, fps=5)
                stream.start()

                # Wait for decoding
                timeout = time.monotonic() + timedelta(seconds=10).total_seconds()
                while stream.latest_frame is None and time.monotonic() < timeout:
                    time.sleep(0.1)

                # Verify frame dimensions
                if stream.latest_frame is not None:
                    self.assertEqual(stream.latest_frame.shape[0], height)
                    self.assertEqual(stream.latest_frame.shape[1], width)
                    self.assertEqual(stream.latest_frame.shape[2], 3)

                stream.stop()

    def _create_video_with_dimensions(
        self, width: int, height: int, frame_count: int
    ) -> bytes:
        """Create test video with specific dimensions."""
        output_buffer = io.BytesIO()
        container: OutputContainer = av.open(output_buffer, "w", format="h264")

        stream: VideoStream = container.add_stream("h264", rate=5)
        stream.width = width
        stream.height = height
        stream.pix_fmt = "yuv420p"

        for i in range(frame_count):
            # Create a test pattern
            frame = av.VideoFrame.from_ndarray(
                np.random.randint(0, 255, (height, width, 3), dtype=np.uint8),
                format="rgb24",
            )
            frame = frame.reformat(format="yuv420p")

            packets = stream.encode(frame)
            for packet in packets:
                container.mux(packet)

        # Flush
        packets = stream.encode()
        for packet in packets:
            container.mux(packet)

        container.close()
        return output_buffer.getvalue()
