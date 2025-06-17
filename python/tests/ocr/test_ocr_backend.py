"""Unit tests for OCR backends with performance benchmarking."""

import time
import unittest
from pathlib import Path

import cv2
import numpy as np
from adb_auto_player.models.geometry.box import Box
from adb_auto_player.models.ocr.ocr_result import OCRResult
from adb_auto_player.ocr.easy_ocr_backend import EasyOCRBackend
from adb_auto_player.ocr.tesseract_backend import TesseractBackend


class TestOCRBackends(unittest.TestCase):
    """Test cases for OCR backend implementations."""

    performance_results: dict[str, list]

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before all tests."""
        cls.test_image = cls._get_test_image(synthetic=False)
        cls.performance_results = {}

    @staticmethod
    def _create_test_image():
        """Create a simple synthetic image with text for testing."""
        img = np.ones((200, 600, 3), dtype=np.uint8) * 255
        # Add some text using OpenCV
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(
            img=img,
            text="Sample Text for OCR Testing",
            org=(50, 80),
            fontFace=font,
            fontScale=1,
            color=(0, 0, 0),
            thickness=2,
        )
        cv2.putText(
            img=img,
            text="Line 2: More Test Content",
            org=(50, 120),
            fontFace=font,
            fontScale=0.8,
            color=(0, 0, 0),
            thickness=2,
        )
        cv2.putText(
            img=img,
            text="123 Numbers and Text",
            org=(50, 160),
            fontFace=font,
            fontScale=0.8,
            color=(0, 0, 0),
            thickness=2,
        )
        cv2.imwrite("test.png", img)
        return img

    @staticmethod
    def _get_test_image(synthetic: bool = True) -> np.ndarray:
        """Return test image.

        Args:
            synthetic: Whether to get a synthetic test image

        Returns:
            np.ndarray: Test image
        """
        if synthetic:
            return TestOCRBackends._create_test_image()

        path = Path(__file__).parent / "data" / "battle_modes.png"
        return cv2.imread(path.as_posix())

    def setUp(self):
        """Set up test fixtures before each test."""
        # Initialize backends
        try:
            self.tesseract_backend = TesseractBackend()
        except RuntimeError as e:
            self.skipTest(f"Tesseract not available: {e}")

        try:
            self.easyocr_backend = EasyOCRBackend(languages=["en"], gpu=False)
        except RuntimeError as e:
            self.skipTest(f"EasyOCR not available: {e}")

    def _time_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """Time an operation and store results.

        Args:
            operation_name: Name of the operation for tracking
            operation_func: Function to time
            *args: args for the function
            **kwargs: kwargs for the function

        Returns:
            tuple: (result, elapsed_time)
        """
        start_time = time.perf_counter()
        result = operation_func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        # Store performance data
        if operation_name not in self.performance_results:
            self.performance_results[operation_name] = []
        self.performance_results[operation_name].append(elapsed_time)

        return result, elapsed_time

    def test_tesseract_extract_text(self):
        """Test Tesseract text extraction."""
        result, elapsed_time = self._time_operation(
            "tesseract_extract_text",
            self.tesseract_backend.extract_text,
            self.test_image,
        )

        self.assertIsInstance(result, str)
        print(f"Tesseract extract_text: {elapsed_time:.3f}s")
        print(f"Extracted text: '{result.strip()}'")

    def test_tesseract_detect_text_with_boxes(self):
        """Test Tesseract text detection with bounding boxes."""
        result, elapsed_time = self._time_operation(
            "tesseract_detect_boxes",
            self.tesseract_backend.detect_text_with_boxes,
            self.test_image,
            min_confidence=0.3,
        )

        self.assertIsInstance(result, list)
        for ocr_result in result:
            self.assertIsInstance(ocr_result, OCRResult)
            self.assertIsInstance(ocr_result.text, str)
            self.assertIsInstance(ocr_result.confidence, float)
            self.assertIsInstance(ocr_result.box, Box)
            self.assertGreaterEqual(ocr_result.confidence, 0.0)
            self.assertLessEqual(ocr_result.confidence, 1.0)

        print(f"Tesseract detect_text_with_boxes: {elapsed_time:.3f}s")
        print(f"Found {len(result)} text regions")
        for i, ocr_result in enumerate(result[:3]):  # Show first 3 results
            print(
                f"  {i + 1}: '{ocr_result.text}' (conf: {ocr_result.confidence:.2f}) "
                f"{ocr_result.box}"
            )

    def test_tesseract_backend_info(self):
        """Test Tesseract backend information."""
        info = self.tesseract_backend.get_backend_info()

        self.assertIsInstance(info, dict)
        self.assertIn("name", info)
        self.assertIn("version", info)
        self.assertIn("config", info)
        self.assertIn("language", info)
        self.assertEqual(info["name"], "Tesseract")

        print(f"Tesseract info: {info}")

    def test_tesseract_preprocess_image(self):
        """Test Tesseract image preprocessing."""
        # Test basic preprocessing
        processed = self.tesseract_backend.preprocess_image(self.test_image)
        self.assertIsInstance(processed, np.ndarray)

        # Test with different options
        processed_denoised = self.tesseract_backend.preprocess_image(
            self.test_image, denoise=True
        )
        self.assertIsInstance(processed_denoised, np.ndarray)

        processed_scaled = self.tesseract_backend.preprocess_image(
            self.test_image, scale_factor=2.0
        )
        self.assertIsInstance(processed_scaled, np.ndarray)

    def test_easyocr_extract_text(self):
        """Test EasyOCR text extraction."""
        result, elapsed_time = self._time_operation(
            "easyocr_extract_text", self.easyocr_backend.extract_text, self.test_image
        )

        self.assertIsInstance(result, str)
        print(f"EasyOCR extract_text: {elapsed_time:.3f}s")
        print(f"Extracted text: '{result.strip()}'")

    def test_easyocr_detect_text_with_boxes(self):
        """Test EasyOCR text detection with bounding boxes."""
        result, elapsed_time = self._time_operation(
            "easyocr_detect_boxes",
            self.easyocr_backend.detect_text_with_boxes,
            self.test_image,
            min_confidence=0.3,
        )

        self.assertIsInstance(result, list)
        for ocr_result in result:
            self.assertIsInstance(ocr_result, OCRResult)
            self.assertIsInstance(ocr_result.text, str)
            self.assertIsInstance(ocr_result.confidence, float)
            self.assertIsInstance(ocr_result.box, Box)
            self.assertGreaterEqual(ocr_result.confidence, 0.0)
            self.assertLessEqual(ocr_result.confidence, 1.0)

        print(f"EasyOCR detect_text_with_boxes: {elapsed_time:.3f}s")
        print(f"Found {len(result)} text regions")
        for i, ocr_result in enumerate(result[:3]):  # Show first 3 results
            print(
                f"  {i + 1}: '{ocr_result.text}' (conf: {ocr_result.confidence:.2f}) "
                f"{ocr_result.box}"
            )

    def test_easyocr_backend_info(self):
        """Test EasyOCR backend information."""
        info = self.easyocr_backend.get_backend_info()

        self.assertIsInstance(info, dict)
        self.assertIn("name", info)
        self.assertIn("languages", info)
        self.assertIn("gpu_enabled", info)
        self.assertEqual(info["name"], "EasyOCR")

        print(f"EasyOCR info: {info}")

    def test_easyocr_set_languages(self):
        """Test EasyOCR language switching."""
        original_languages = self.easyocr_backend.languages.copy()

        # Test changing languages
        new_languages = ["en"]
        self.easyocr_backend.set_languages(new_languages)
        self.assertEqual(self.easyocr_backend.languages, new_languages)

        # Restore original languages
        self.easyocr_backend.set_languages(original_languages)
        self.assertEqual(self.easyocr_backend.languages, original_languages)

    def test_easyocr_detect_and_recognize(self):
        """Test EasyOCR combined detection and recognition."""
        result, elapsed_time = self._time_operation(
            "easyocr_detect_and_recognize",
            self.easyocr_backend.detect_and_recognize,
            self.test_image,
            min_confidence=0.3,
        )

        # Unpack the tuple returned by detect_and_recognize
        results, text = result

        self.assertIsInstance(results, list)
        self.assertIsInstance(text, str)

        print(f"EasyOCR detect_and_recognize: {elapsed_time:.3f}s")
        print(f"Combined text: '{text.strip()}'")

    def test_error_handling(self):
        """Test error handling for invalid inputs."""
        # Test with invalid image (empty array)
        empty_image = np.array([])

        with self.assertRaises(Exception):
            self.tesseract_backend.extract_text(empty_image)

        with self.assertRaises(Exception):
            self.easyocr_backend.extract_text(empty_image)

    def test_confidence_filtering(self):
        """Test confidence filtering works correctly."""
        # Test with high confidence threshold
        high_conf_results = self.tesseract_backend.detect_text_with_boxes(
            self.test_image, min_confidence=0.8
        )

        low_conf_results = self.tesseract_backend.detect_text_with_boxes(
            self.test_image, min_confidence=0.1
        )

        # High confidence should have fewer or equal results
        self.assertLessEqual(len(high_conf_results), len(low_conf_results))

        # All results should meet confidence threshold
        for result in high_conf_results:
            self.assertGreaterEqual(result.confidence, 0.8)

    def test_performance_comparison(self):
        """Run performance comparison between backends."""
        print("\n" + "=" * 60)
        print("PERFORMANCE COMPARISON")
        print("=" * 60)

        # Run multiple iterations for better average
        iterations = 3

        tesseract_times = []
        easyocr_times = []

        for i in range(iterations):
            print(f"\nIteration {i + 1}/{iterations}")

            # Tesseract performance
            _, t_time = self._time_operation(
                f"tesseract_perf_{i}",
                self.tesseract_backend.extract_text,
                self.test_image,
            )
            tesseract_times.append(t_time)

            # EasyOCR performance
            _, e_time = self._time_operation(
                f"easyocr_perf_{i}", self.easyocr_backend.extract_text, self.test_image
            )
            easyocr_times.append(e_time)

            print(f"  Tesseract: {t_time:.3f}s")
            print(f"  EasyOCR:   {e_time:.3f}s")

        # Calculate averages
        avg_tesseract = sum(tesseract_times) / len(tesseract_times)
        avg_easyocr = sum(easyocr_times) / len(easyocr_times)

        print(f"\nAVERAGE PERFORMANCE ({iterations} iterations):")
        print(f"  Tesseract: {avg_tesseract:.3f}s")
        print(f"  EasyOCR:   {avg_easyocr:.3f}s")

        if avg_tesseract < avg_easyocr:
            speedup = avg_easyocr / avg_tesseract
            print(f"  Tesseract is {speedup:.1f}x faster")
        else:
            speedup = avg_tesseract / avg_easyocr
            print(f"  EasyOCR is {speedup:.1f}x faster")

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        print("\n" + "=" * 60)
        print("FINAL PERFORMANCE SUMMARY")
        print("=" * 60)

        for operation, times in cls.performance_results.items():
            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                print(f"{operation}:")
                print(f"  Average: {avg_time:.3f}s")
                print(f"  Min:     {min_time:.3f}s")
                print(f"  Max:     {max_time:.3f}s")
                print(f"  Runs:    {len(times)}")
                print()


class TestOCRBackendsIntegration(unittest.TestCase):
    """Integration tests for OCR backends."""

    def setUp(self):
        """Set up integration test fixtures."""
        self.test_image = TestOCRBackends._get_test_image()

    def test_backend_interface_compliance(self):
        """Test that both backends comply with the OCRBackend interface."""
        try:
            tesseract = TesseractBackend()

            # Test interface methods exist
            self.assertTrue(hasattr(tesseract, "extract_text"))
            self.assertTrue(hasattr(tesseract, "detect_text_with_boxes"))
            self.assertTrue(hasattr(tesseract, "get_backend_info"))

            # Test methods return correct types
            text = tesseract.extract_text(self.test_image)
            self.assertIsInstance(text, str)

            results = tesseract.detect_text_with_boxes(self.test_image)
            self.assertIsInstance(results, list)

            info = tesseract.get_backend_info()
            self.assertIsInstance(info, dict)

        except RuntimeError:
            self.skipTest("Tesseract not available")

        try:
            easyocr = EasyOCRBackend(gpu=False)

            # Test interface methods exist
            self.assertTrue(hasattr(easyocr, "extract_text"))
            self.assertTrue(hasattr(easyocr, "detect_text_with_boxes"))
            self.assertTrue(hasattr(easyocr, "get_backend_info"))

            # Test methods return correct types
            text = easyocr.extract_text(self.test_image)
            self.assertIsInstance(text, str)

            results = easyocr.detect_text_with_boxes(self.test_image)
            self.assertIsInstance(results, list)

            info = easyocr.get_backend_info()
            self.assertIsInstance(info, dict)

        except RuntimeError:
            self.skipTest("EasyOCR not available")


def run_benchmarks():
    """Run performance benchmarks specifically."""
    suite = unittest.TestSuite()
    suite.addTest(TestOCRBackends("test_performance_comparison"))

    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


if __name__ == "__main__":
    # You can run specific tests or benchmarks
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "benchmark":
        run_benchmarks()
    else:
        # Run all tests
        unittest.main(verbosity=2)
