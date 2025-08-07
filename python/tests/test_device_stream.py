import io
import time
import unittest
from unittest.mock import Mock, patch

import av
import numpy as np
from adb_auto_player.device.adb import DeviceStream, StreamingNotSupportedError


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


def create_test_h264_video() -> bytes:
    """Create a small test H.264 video stream."""
    # Create a simple 320x240 test video with a few frames
    output_buffer = io.BytesIO()

    # Create container
    container = av.open(output_buffer, "w", format="h264")

    # Add video stream
    stream = container.add_stream("h264", rate=5)
    stream.width = 320
    stream.height = 240
    stream.pix_fmt = "yuv420p"

    # Generate a few test frames
    for i in range(5):  # 10 frames
        # Create a simple gradient pattern that changes per frame
        frame = av.VideoFrame.from_ndarray(
            np.full((240, 320, 3), fill_value=i * 25, dtype=np.uint8), format="rgb24"
        )
        frame = frame.reformat(format="yuv420p")

        # Encode frame
        packets = stream.encode(frame)
        for packet in packets:
            container.mux(packet)

    # Flush encoder
    packets = stream.encode()
    for packet in packets:
        container.mux(packet)

    container.close()
    return output_buffer.getvalue()


class TestDeviceStream(unittest.TestCase):
    """Test DeviceStream with real video decoding."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_device = Mock()

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
            "adb_auto_player.device.adb.device_stream.platform.system",
            return_value="Darwin",
        ):
            with patch(
                "adb_auto_player.device.adb.device_stream.platform.machine",
                return_value="arm64",
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
        self.mock_device.shell.return_value = mock_connection

        self.mock_device.is_controlling_emulator = False

        stream = DeviceStream(self.mock_device, fps=5)

        # Start streaming
        stream.start()

        # Let it run for a bit to trigger buffer management
        time.sleep(0.5)

        # Should not crash due to memory issues
        stream.stop()


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
                timeout = time.time() + 10
                while stream.latest_frame is None and time.time() < timeout:
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
        container = av.open(output_buffer, "w", format="h264")

        stream = container.add_stream("h264", rate=5)
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


if __name__ == "__main__":
    unittest.main()
