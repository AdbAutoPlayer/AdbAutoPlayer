import unittest
from unittest.mock import patch, MagicMock
import adb_auto_player.logging_setup


class TestSanitizePath(unittest.TestCase):
    @patch("os.path.expanduser", return_value=r"C:\Users\mockuser")
    def test_windows_path(self, mock_expanduser: MagicMock):
        log = rf"adb_path: {mock_expanduser.return_value}\AppData\Local\file.txt"
        expected = r"adb_path: C:\Users\{redacted}\AppData\Local\file.txt"
        self.assertEqual(expected, adb_auto_player.logging_setup.sanitize_path(log))

    @patch("os.path.expanduser", return_value=r"C:\\Users\\mockuser")
    def test_windows_path_double_backslash(self, mock_expanduser: MagicMock):
        log = f"No such file or directory: '{mock_expanduser.return_value}"
        r"\\GolandProjects\\AdbAutoPlayer\\python\\config.toml"
        expected = r"No such file or directory: 'C:\\Users\\{redacted}"
        r"\\GolandProjects\\AdbAutoPlayer\\python\\config.toml"
        self.assertEqual(expected, adb_auto_player.logging_setup.sanitize_path(log))

    @patch("os.path.expanduser", return_value="/home/mockuser")
    def test_unix_path(self, mock_expanduser: MagicMock):
        log = f"{mock_expanduser.return_value}/.config/file.txt"
        expected = "/home/{redacted}/.config/file.txt"
        self.assertEqual(expected, adb_auto_player.logging_setup.sanitize_path(log))

    @patch("os.path.expanduser", return_value=r"C:\Users\mockuser")
    def test_multiple_occurrences(self, mock_expanduser: MagicMock):
        log = rf"adb_path: {mock_expanduser.return_value}\AppData\file.txt"
        r" and D:\Users\mockuser\Desktop\file2.txt"
        expected = r"adb_path: C:\Users\{redacted}\AppData\file.txt"
        r" and D:\Users\{redacted}\Desktop\file2.txt"
        self.assertEqual(expected, adb_auto_player.logging_setup.sanitize_path(log))
