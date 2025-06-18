"""Unit tests for the Threshold dataclass."""

import unittest

from adb_auto_player.models.threshold import Threshold


class TestThreshold(unittest.TestCase):
    """Test cases for Threshold class."""

    def test_percentage_strings(self):
        """Test percentage string inputs."""
        # Basic percentages
        self.assertAlmostEqual(Threshold("80%").value, 0.8)
        self.assertAlmostEqual(Threshold("95%").value, 0.95)
        self.assertAlmostEqual(Threshold("0%").value, 0.0)
        self.assertAlmostEqual(Threshold("100%").value, 1.0)

        # Decimal percentages
        self.assertAlmostEqual(Threshold("85.5%").value, 0.855)
        self.assertAlmostEqual(Threshold("12.34%").value, 0.1234)

        # With spaces (your improvement)
        self.assertAlmostEqual(Threshold("70 %").value, 0.7)
        self.assertAlmostEqual(Threshold(" 80%").value, 0.8)
        self.assertAlmostEqual(Threshold(" 90 %").value, 0.9)
        self.assertAlmostEqual(Threshold("75.5 %").value, 0.755)

    def test_normalized_floats(self):
        """Test normalized float inputs (0.0-1.0)."""
        self.assertAlmostEqual(Threshold(0.8).value, 0.8)
        self.assertAlmostEqual(Threshold(0.95).value, 0.95)
        self.assertAlmostEqual(Threshold(0.0).value, 0.0)
        self.assertAlmostEqual(Threshold(1.0).value, 1.0)
        self.assertAlmostEqual(Threshold(0.123).value, 0.123)

    def test_integer_percentages(self):
        """Test integer percentage inputs (0-100)."""
        self.assertAlmostEqual(Threshold(80).value, 0.8)
        self.assertAlmostEqual(Threshold(95).value, 0.95)
        self.assertAlmostEqual(Threshold(0).value, 0.0)
        self.assertAlmostEqual(Threshold(100).value, 1.0)
        self.assertAlmostEqual(Threshold(1).value, 0.01)

    def test_string_numbers(self):
        """Test string number inputs."""
        # Normalized strings
        self.assertAlmostEqual(Threshold("0.8").value, 0.8)
        self.assertAlmostEqual(Threshold("0.95").value, 0.95)
        self.assertAlmostEqual(Threshold("1.0").value, 1.0)
        self.assertAlmostEqual(Threshold("0.0").value, 0.0)

        # Percentage strings (without %)
        self.assertAlmostEqual(Threshold("80").value, 0.8)
        self.assertAlmostEqual(Threshold("95").value, 0.95)
        self.assertAlmostEqual(Threshold("100").value, 1.0)

        # With whitespace
        self.assertAlmostEqual(Threshold(" 0.8 ").value, 0.8)
        self.assertAlmostEqual(Threshold(" 80 ").value, 0.8)

    def test_conversion_methods(self):
        """Test conversion methods."""
        threshold = Threshold("80%")

        self.assertAlmostEqual(threshold.to_normalized(), 0.8)
        self.assertAlmostEqual(threshold.to_percentage(), 80.0)
        self.assertAlmostEqual(threshold.to_tesseract_format(), 80.0)
        self.assertAlmostEqual(float(threshold), 0.8)

    def test_string_representations(self):
        """Test string representations."""
        threshold = Threshold("80%")

        self.assertEqual(str(threshold), "80.0%")
        self.assertEqual(repr(threshold), "Threshold(0.8)")

    def test_equality_comparisons(self):
        """Test equality comparisons."""
        t1 = Threshold("80%")
        t2 = Threshold(0.8)
        t3 = Threshold(80)
        t4 = Threshold("0.8")
        t5 = Threshold("90%")

        # Same value, different formats
        self.assertEqual(t1, t2)
        self.assertEqual(t1, t3)
        self.assertEqual(t1, t4)
        self.assertEqual(t2, t3)
        self.assertEqual(t2, t4)
        self.assertEqual(t3, t4)

        # Different values
        self.assertNotEqual(t1, t5)

        # Compare with raw values
        self.assertEqual(t1, 0.8)
        self.assertEqual(t1, 80)  # Should normalize 80 to 0.8
        self.assertNotEqual(t1, 0.9)

    def test_ordering_comparisons(self):
        """Test ordering comparisons."""
        t1 = Threshold("70%")  # 0.7
        t2 = Threshold("80%")  # 0.8
        t3 = Threshold("90%")  # 0.9

        # Less than
        self.assertTrue(t1 < t2)
        self.assertTrue(t2 < t3)
        self.assertFalse(t2 < t1)

        # Less than or equal
        self.assertTrue(t1 <= t2)
        self.assertTrue(t1 <= Threshold("70%"))
        self.assertFalse(t2 <= t1)

        # Greater than
        self.assertTrue(t3 > t2)
        self.assertTrue(t2 > t1)
        self.assertFalse(t1 > t2)

        # Greater than or equal
        self.assertTrue(t3 >= t2)
        self.assertTrue(t2 >= Threshold("80%"))
        self.assertFalse(t1 >= t2)

        # Compare with raw values
        self.assertTrue(t2 > 0.7)
        self.assertTrue(t2 < 0.9)
        self.assertTrue(t2 == 80)

    def test_edge_cases(self):
        """Test edge cases and boundary values."""
        # Boundary values
        self.assertAlmostEqual(Threshold("0%").value, 0.0)
        self.assertAlmostEqual(Threshold("100%").value, 1.0)
        self.assertAlmostEqual(Threshold(0.0).value, 0.0)
        self.assertAlmostEqual(Threshold(1.0).value, 1.0)
        self.assertAlmostEqual(Threshold(0).value, 0.0)
        self.assertAlmostEqual(Threshold(100).value, 1.0)

        # Very small values
        self.assertAlmostEqual(Threshold("0.1%").value, 0.001)
        self.assertAlmostEqual(Threshold(0.001).value, 0.001)

        # Near boundary values
        self.assertAlmostEqual(Threshold("99.9%").value, 0.999)
        self.assertAlmostEqual(Threshold(0.999).value, 0.999)

    def test_boolean(self):
        self.assertAlmostEqual(Threshold(True).value, 1.0)
        self.assertAlmostEqual(Threshold(False).value, 0.0)

    def test_invalid_inputs(self):
        """Test invalid inputs raise appropriate errors."""
        # Invalid percentage values
        with self.assertRaises(ValueError):
            Threshold("101%")
        with self.assertRaises(ValueError):
            Threshold("-10%")
        with self.assertRaises(ValueError):
            Threshold("150%")

        # Invalid numeric values
        with self.assertRaises(ValueError):
            Threshold(1.5)
        with self.assertRaises(ValueError):
            Threshold(-0.1)
        with self.assertRaises(ValueError):
            Threshold(101)
        with self.assertRaises(ValueError):
            Threshold(-10)

        # Invalid string formats
        with self.assertRaises(ValueError):
            Threshold("abc%")
        with self.assertRaises(ValueError):
            Threshold("80%%")
        with self.assertRaises(ValueError):
            Threshold("%.80")
        with self.assertRaises(ValueError):
            Threshold("abc")
        with self.assertRaises(ValueError):
            Threshold("")
        with self.assertRaises(ValueError):
            Threshold(" ")

        # Invalid types
        with self.assertRaises(ValueError):
            Threshold(None)
        with self.assertRaises(ValueError):
            Threshold([80])
        with self.assertRaises(ValueError):
            Threshold({"value": 80})

    def test_error_messages(self):
        """Test that error messages are informative."""
        # Test percentage out of range
        with self.assertRaisesRegex(
            ValueError, "Percentage must be between 0% and 100%"
        ):
            Threshold("150%")

        # Test invalid percentage format
        with self.assertRaisesRegex(
            ValueError,
            "Invalid percentage format",
        ):
            Threshold("abc%")

        # Test invalid threshold format
        with self.assertRaisesRegex(ValueError, "Invalid threshold format"):
            Threshold("xyz")

        # Test out of range numeric
        with self.assertRaisesRegex(
            ValueError, "Threshold must be between 0-1 or 0-100"
        ):
            Threshold(150)

        # Test unsupported type
        with self.assertRaisesRegex(ValueError, "Unsupported threshold type"):
            Threshold(None)

    def test_whitespace_handling(self):
        """Test various whitespace scenarios."""
        # Leading/trailing spaces
        self.assertAlmostEqual(Threshold("  80%  ").value, 0.8)
        self.assertAlmostEqual(Threshold("  0.8  ").value, 0.8)
        self.assertAlmostEqual(Threshold("  80  ").value, 0.8)

        # Spaces around percent sign
        self.assertAlmostEqual(Threshold("80 %").value, 0.8)
        self.assertAlmostEqual(Threshold(" 80 % ").value, 0.8)

        # Multiple spaces
        self.assertAlmostEqual(Threshold("80  %").value, 0.8)
        self.assertAlmostEqual(Threshold("  80  %  ").value, 0.8)

    def test_decimal_precision(self):
        """Test decimal precision handling."""
        # High precision values
        self.assertAlmostEqual(Threshold("85.555%").value, 0.85555, places=5)
        self.assertAlmostEqual(Threshold(0.85555).value, 0.85555, places=5)
        self.assertAlmostEqual(Threshold("0.85555").value, 0.85555, places=5)

        # Very small differences
        t1 = Threshold(0.8)
        t2 = Threshold(0.8000000001)
        # Should be equal due to floating point precision handling
        self.assertEqual(t1, t2)

    def test_special_float_values(self):
        """Test special float values."""
        # Test that we don't accept infinity or NaN
        with self.assertRaises(ValueError):
            Threshold(float("inf"))
        with self.assertRaises(ValueError):
            Threshold(float("-inf"))
        with self.assertRaises(ValueError):
            Threshold(float("nan"))

    def test_comprehensive_equivalence(self):
        """Test that all equivalent representations are truly equal."""
        # All these should represent 80%
        equivalent_values = [
            "80%",
            "80 %",
            " 80%",
            " 80 %",
            "80.0%",
            "80.00%",
            0.8,
            0.80,
            80,
            "80",
            "0.8",
            "0.80",
        ]

        thresholds = [Threshold(val) for val in equivalent_values]

        # All should be equal to each other
        for i, t1 in enumerate(thresholds):
            for j, t2 in enumerate(thresholds):
                self.assertEqual(
                    t1,
                    t2,
                    msg=(
                        f"Threshold({equivalent_values[i]}) "
                        f"!= Threshold({equivalent_values[j]})"
                    ),
                )

            # All should equal 0.8
            self.assertAlmostEqual(t1.value, 0.8, places=10)
