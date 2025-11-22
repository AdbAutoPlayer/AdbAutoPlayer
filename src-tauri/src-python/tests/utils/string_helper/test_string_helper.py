import unittest

from adb_auto_player.util import StringHelper


class TestStringHelper(unittest.TestCase):
    def test_get_filename_without_extension_basic(self):
        path = "/path/to/file.txt"
        result = StringHelper.get_filename_without_extension(path)
        self.assertEqual(result, "file")

    def test_get_filename_without_extension_no_extension(self):
        path = "/path/to/document"
        result = StringHelper.get_filename_without_extension(path)
        self.assertEqual(result, "document")

    def test_get_filename_without_extension_multiple_dots(self):
        path = "/path/to/archive.tar.gz"
        result = StringHelper.get_filename_without_extension(path)
        self.assertEqual(result, "archive.tar")


if __name__ == "__main__":
    unittest.main()
