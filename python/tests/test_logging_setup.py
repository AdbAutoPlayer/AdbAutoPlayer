import unittest
from unittest.mock import patch
import adb_auto_player.logging_setup


class TestSanitizePath(unittest.TestCase):

    @patch("os.path.expanduser", return_value=r"C:\Users\mockuser")  # Mock home dir
    def test_windows_path(self, mock_expanduser):
        log = r"adb_path: C:\Users\mockuser\AppData\Local\file.txt"
        expected = r"adb_path: C:\Users\<redacted>\AppData\Local\file.txt"
        self.assertEqual(expected, adb_auto_player.logging_setup.sanitize_path(log))

    @patch("os.path.expanduser", return_value="/home/mockuser")  # Mock home dir
    def test_unix_path(self, mock_expanduser):
        log = "/home/mockuser/.config/file.txt"
        expected = "/home/<redacted>/.config/file.txt"
        self.assertEqual(expected, adb_auto_player.logging_setup.sanitize_path(log))

    @patch("os.path.expanduser", return_value=r"C:\Users\mockuser")
    def test_multiple_occurrences(self, mock_expanduser):
        log = r"adb_path: C:\Users\mockuser\AppData\file.txt"
        r" and D:\Users\mockuser\Desktop\file2.txt"
        expected = r"adb_path: C:\Users\<redacted>\AppData\file.txt"
        r" and D:\Users\<redacted>\Desktop\file2.txt"
        self.assertEqual(expected, adb_auto_player.logging_setup.sanitize_path(log))


if __name__ == "__main__":
    unittest.main()
