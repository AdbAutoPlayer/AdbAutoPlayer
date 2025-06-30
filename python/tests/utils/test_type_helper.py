import unittest

import numpy as np
from adb_auto_player.util import TypeHelper


class TestNumpyHelpers(unittest.TestCase):
    def test_with_python_int(self):
        self.assertIs(TypeHelper.to_int_if_needed(42), 42)
        self.assertIs(TypeHelper.to_int_if_needed(0), 0)

    def test_with_numpy_int64(self):
        np_int = np.int64(123)
        result = TypeHelper.to_int_if_needed(np_int)
        self.assertEqual(result, 123)
        self.assertIsInstance(result, np.integer)

    def test_with_numpy_int32(self):
        np_int = np.int32(123)
        result = TypeHelper.to_int_if_needed(np_int)
        self.assertEqual(result, 123)
        self.assertIsInstance(result, np.integer)

    def test_with_string_number(self):
        self.assertEqual(TypeHelper.to_int_if_needed("10"), 10)
        self.assertIsInstance(TypeHelper.to_int_if_needed("10"), int)

    def test_with_float_number(self):
        self.assertEqual(TypeHelper.to_int_if_needed(10.7), 10)
        self.assertIsInstance(TypeHelper.to_int_if_needed(10.7), int)

    def test_with_bool(self):
        # bool is subclass of int, so should return as is
        self.assertIs(TypeHelper.to_int_if_needed(True), True)
        self.assertIs(TypeHelper.to_int_if_needed(False), False)

    def test_with_numpy_bool(self):
        np_bool = np.bool_(True)
        result = TypeHelper.to_int_if_needed(np_bool)
        self.assertEqual(result, 1)
        self.assertIsInstance(result, int)
