import unittest

from adb_auto_player.models.geometry.box import Box
from adb_auto_player.models.geometry.point import Point


class TestBox(unittest.TestCase):
    def test_valid_initialization_and_properties(self):
        box = Box(x=10, y=20, width=30, height=40)

        self.assertEqual(box.x, 10)
        self.assertEqual(box.y, 20)
        self.assertEqual(box.width, 30)
        self.assertEqual(box.height, 40)

        self.assertEqual(box.left, 10)
        self.assertEqual(box.top, 20)
        self.assertEqual(box.right, 40)  # 10 + 30
        self.assertEqual(box.bottom, 60)  # 20 + 40

        self.assertEqual(box.top_left, Point(10, 20))
        self.assertEqual(box.top_right, Point(40, 20))
        self.assertEqual(box.bottom_left, Point(10, 60))
        self.assertEqual(box.bottom_right, Point(40, 60))
        self.assertEqual(box.center, Point(10 + 30 // 2, 20 + 40 // 2))
        self.assertEqual(box.area, 30 * 40)

    def test_invalid_initialization(self):
        # Negative x or y should raise ValueError
        with self.assertRaises(ValueError):
            Box(x=-1, y=0, width=10, height=10)

        with self.assertRaises(ValueError):
            Box(x=0, y=-5, width=10, height=10)

        # Zero or negative width/height should raise ValueError
        with self.assertRaises(ValueError):
            Box(x=0, y=0, width=0, height=10)

        with self.assertRaises(ValueError):
            Box(x=0, y=0, width=10, height=0)

        with self.assertRaises(ValueError):
            Box(x=0, y=0, width=-5, height=10)

        with self.assertRaises(ValueError):
            Box(x=0, y=0, width=10, height=-5)

    def test_contains(self):
        box = Box(5, 5, 10, 10)

        # Inside points
        self.assertTrue(box.contains(Point(5, 5)))  # top-left corner
        self.assertTrue(box.contains(Point(14, 14)))  # just inside bottom-right
        self.assertTrue(box.contains(Point(10, 10)))  # center-ish

        # Outside points
        self.assertFalse(box.contains(Point(4, 5)))  # left outside
        self.assertFalse(box.contains(Point(5, 4)))  # above
        self.assertFalse(box.contains(Point(15, 15)))  # right-bottom outside
        self.assertFalse(box.contains(Point(15, 14)))  # right outside
        self.assertFalse(box.contains(Point(14, 15)))  # bottom outside

    def test_str_repr(self):
        box = Box(1, 2, 3, 4)
        self.assertEqual(str(box), "Box(x=1, y=2, w=3, h=4)")

    def test_random_point_no_margin(self):
        box = Box(0, 0, 10, 10)
        for _ in range(100):
            p = box.random_point()
            self.assertTrue(box.contains(p))

    def test_random_point_with_float_margin(self):
        box = Box(0, 0, 100, 100)
        margin = 0.1  # 10% margin
        for _ in range(100):
            p = box.random_point(margin=margin)
            self.assertTrue(box.contains(p))
            # Check point is within margin bounds:
            self.assertGreaterEqual(p.x, box.x + int(box.width * margin))
            self.assertLess(p.x, box.right - int(box.width * margin))
            self.assertGreaterEqual(p.y, box.y + int(box.height * margin))
            self.assertLess(p.y, box.bottom - int(box.height * margin))

    def test_random_point_with_percentage_string_margin(self):
        box = Box(0, 0, 100, 100)
        margin = "20%"
        for _ in range(100):
            p = box.random_point(margin=margin)
            self.assertTrue(box.contains(p))
            margin_val = 0.2
            self.assertGreaterEqual(p.x, box.x + int(box.width * margin_val))
            self.assertLess(p.x, box.right - int(box.width * margin_val))
            self.assertGreaterEqual(p.y, box.y + int(box.height * margin_val))
            self.assertLess(p.y, box.bottom - int(box.height * margin_val))

    def test_random_point_margin_edge_cases(self):
        box = Box(0, 0, 10, 10)

        # Margin too high (>=0.5) raises ValueError
        with self.assertRaises(ValueError):
            box.random_point(margin=0.5)

        with self.assertRaises(ValueError):
            box.random_point(margin=1.0)

        # Negative margin raises ValueError
        with self.assertRaises(ValueError):
            box.random_point(margin=-0.1)

        # Invalid string margin format
        with self.assertRaises(ValueError):
            box.random_point(margin="30")

        with self.assertRaises(ValueError):
            box.random_point(margin="abc%")

    def test_random_point_when_no_room_due_to_margin(self):
        box = Box(0, 0, 1, 1)
        p = box.random_point(margin=0.4)
        self.assertTrue(box.contains(p))

        p = box.random_point(margin=0.49)
        self.assertTrue(box.contains(p))


if __name__ == "__main__":
    unittest.main()
