import unittest

import numpy as np
from adb_auto_player.models.geometry.point import Point


class TestPoint(unittest.TestCase):
    def test_point_creation_valid(self):
        p = Point(3, 4)
        self.assertEqual(p.x, 3)
        self.assertEqual(p.y, 4)

    def test_point_creation_invalid_negative(self):
        with self.assertRaises(ValueError):
            Point(-1, 5)
        with self.assertRaises(ValueError):
            Point(3, -2)

    def test_distance_to(self):
        p1 = Point(0, 0)
        p2 = Point(3, 4)
        self.assertAlmostEqual(p1.distance_to(p2), 5.0)

    def test_is_close_to_true_and_false(self):
        p1 = Point(0, 0)
        p2 = Point(3, 4)
        self.assertTrue(p1.is_close_to(p2, 6.0))  # 5 < 6
        self.assertFalse(p1.is_close_to(p2, 4.9))  # 5 > 4.9

    def test_from_numpy_valid(self):
        arr = np.array([7.0, 8.0])
        p = Point.from_numpy(arr)
        self.assertEqual(p.x, 7)
        self.assertEqual(p.y, 8)

    def test_from_numpy_invalid_shape(self):
        with self.assertRaises(AssertionError):
            Point.from_numpy(np.array([1, 2, 3]))

    def test_to_numpy(self):
        p = Point(5, 6)
        arr = p.to_numpy()
        self.assertIsInstance(arr, np.ndarray)
        self.assertEqual(arr.shape, (2,))
        self.assertEqual(arr[0], 5)
        self.assertEqual(arr[1], 6)
        # Test np_int as well
        p = Point(np.int64(5), np.int64(6))
        arr = p.to_numpy()
        self.assertIsInstance(arr, np.ndarray)
        self.assertEqual(arr.shape, (2,))
        self.assertEqual(arr[0], np.int64(5))
        self.assertEqual(arr[1], np.int64(6))

    def test_str_representation(self):
        p = Point(10, 20)
        self.assertEqual(str(p), "Point(x=10, y=20)")
        # Test np_int as well
        p = Point(np.int64(10), np.int64(20))
        self.assertEqual(str(p), "Point(x=10, y=20)")
