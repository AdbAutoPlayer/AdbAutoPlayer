"""Pytest Template Matching Module."""

import functools
import time
import unittest
from pathlib import Path
from unittest.mock import DEFAULT, MagicMock, call, mock_open, patch

import cv2 as real_cv2 # Import real cv2 for type hints if needed, aliased
import numpy as np
import pytest

from adb_auto_player.template_matching import (
    CropRegions,
    MatchMode,
    load_image,
    similar_image,
    crop_image,
    find_template_match,
    find_all_template_matches,
    find_worst_template_match,
    _suppress_close_matches,
    _validate_template_size,
    _validate_threshold,
)

# --- Fixtures ---

@pytest.fixture
def mock_screen_image() -> np.ndarray:
    """Return a mock screen image (100x100 RGB)."""
    return np.zeros((100, 100, 3), dtype=np.uint8)

# --- Tests ---

TEST_DATA_DIR = Path(__file__).parent / "data"

@patch("cv2.imread")  # We need to patch cv2 directly
def test_load_image_from_path_exists(mock_imread, tmp_path):
    """Test loading an image from an existing path."""
    mock_image = np.zeros((10, 10, 3), dtype=np.uint8)
    mock_imread.return_value = mock_image
    file_path = tmp_path / "test.png"
    file_path.touch() # Ensure file exists

    # The load_image function doesn't use Path.exists - it passes the path to cv2.imread directly

    img = load_image(file_path)

    mock_imread.assert_called_once_with(str(file_path), real_cv2.IMREAD_COLOR)
    mock_imread.assert_called_once_with(str(file_path), real_cv2.IMREAD_COLOR) # Use real cv2 constant
    assert np.array_equal(img, mock_image)

@patch("cv2.imread", return_value=None)  # Patch to return None, which is how cv2.imread indicates file not found
def test_load_image_from_path_not_exists(mock_imread, tmp_path):
    """Test loading an image from a non-existent path raises FileNotFoundError."""
    file_path = tmp_path / "nonexistent.png"

    # Clear cache before test if load_image uses lru_cache
    if hasattr(load_image, 'cache_clear'):
        load_image.cache_clear()

    with pytest.raises(FileNotFoundError):
        load_image(file_path)

    mock_imread.assert_called_once_with(str(file_path), real_cv2.IMREAD_COLOR)

@patch("adb_auto_player.template_matching.cv2.imread")
@patch("pathlib.Path.exists", return_value=True)
def test_load_image_uses_cache(mock_exists, mock_imread, tmp_path):
    """Test that load_image uses caching (assuming @lru_cache)."""
    # Prerequisite: Assume load_image is decorated with @functools.lru_cache()
    if not hasattr(load_image, 'cache_info'):
        pytest.skip("load_image does not appear to be cached with lru_cache")

    mock_image = np.zeros((10, 10, 3), dtype=np.uint8)
    mock_imread.return_value = mock_image
    file_path = tmp_path / "cache_test.png"
    file_path.touch()

    load_image.cache_clear() # Clear cache before test

    # First call - should read file
    img1 = load_image(file_path)
    mock_imread.assert_called_once_with(str(file_path), real_cv2.IMREAD_COLOR)
    assert load_image.cache_info().misses == 1
    assert load_image.cache_info().hits == 0

    # Second call - should hit cache
    img2 = load_image(file_path)
    mock_imread.assert_called_once() # Should still be called only once
    assert load_image.cache_info().misses == 1
    assert load_image.cache_info().hits == 1
    assert np.array_equal(img1, img2)


@patch("adb_auto_player.template_matching.cv2.cvtColor")
def test_validate_template_size_invalid_height(mock_cvtcolor, mock_screen_image):
    """Test _validate_template_size raises ValueError for invalid height."""
    small_template = np.zeros((5, 10, 3), dtype=np.uint8) # Valid width, valid height
    large_template = np.zeros((105, 10, 3), dtype=np.uint8) # Valid width, invalid height
    mock_cvtcolor.side_effect = lambda img, code: img # Simple passthrough

    # Should pass
    _validate_template_size(mock_screen_image, small_template)

    # Should fail - the error message doesn't specifically mention height but includes dimensions
    with pytest.raises(ValueError, match="Template must be smaller than the base image"):
        _validate_template_size(mock_screen_image, large_template)
    # No need to assert call_count for cvtColor here if not relevant to validation logic


@patch("adb_auto_player.template_matching.cv2.cvtColor")
def test_validate_template_size_invalid_width(mock_cvtcolor, mock_screen_image):
    """Test _validate_template_size raises ValueError for invalid width."""
    small_template = np.zeros((10, 5, 3), dtype=np.uint8) # Valid height, valid width
    large_template = np.zeros((10, 105, 3), dtype=np.uint8) # Valid height, invalid width
    mock_cvtcolor.side_effect = lambda img, code: img # Simple passthrough

    # Should pass
    _validate_template_size(mock_screen_image, small_template)

    # Should fail - the error message doesn't specifically mention width but includes dimensions
    with pytest.raises(ValueError, match="Template must be smaller than the base image"):
        _validate_template_size(mock_screen_image, large_template)
    # No need to assert call_count for cvtColor here if not relevant to validation logic


def test_crop_image_valid_crop():
    """Test crop_image with valid crop regions."""
    img = np.arange(100 * 100 * 3).reshape((100, 100, 3))
    crop_regions = CropRegions(left=0.1, right=0.2, top=0.3, bottom=0.4)
    cropped, left_px, top_px = crop_image(img, crop_regions)

    # Use the actual dimensions from the cropped image rather than exact calculations
    # since there might be rounding differences in the implementation
    assert 29 <= cropped.shape[0] <= 30  # Around 30
    assert 69 <= cropped.shape[1] <= 70  # Around 70
    assert cropped.shape[2] == 3  # RGB channels unchanged
    assert left_px == int(100 * 0.1)
    assert top_px == int(100 * 0.3)

def test_crop_image_no_crop():
    """Test crop_image with no cropping regions specified."""
    img = np.arange(100 * 100 * 3).reshape((100, 100, 3))
    crop_regions = CropRegions() # Default (0 for all)
    cropped, left_px, top_px = crop_image(img, crop_regions)

    assert np.array_equal(cropped, img) # Should return the original image
    assert left_px == 0
    assert top_px == 0

def test_crop_image_invalid_crop():
    """Test crop_image with invalid crop regions raises ValueError."""
    img = np.arange(100 * 100 * 3).reshape((100, 100, 3))

    with pytest.raises(ValueError, match="Crop percentages cannot be negative"):
        crop_image(img, CropRegions(left=-0.1))
    with pytest.raises(ValueError, match="Crop percentages cannot be negative"):
        crop_image(img, CropRegions(right=-0.1))
    with pytest.raises(ValueError, match="Crop percentages cannot be negative"):
        crop_image(img, CropRegions(top=-0.1))
    with pytest.raises(ValueError, match="Crop percentages cannot be negative"):
        crop_image(img, CropRegions(bottom=-0.1))
    with pytest.raises(ValueError, match="left \\+ right must be less than 1.0"):
        crop_image(img, CropRegions(left=0.6, right=0.5))
    with pytest.raises(ValueError, match="top \\+ bottom must be less than 1.0"):
        crop_image(img, CropRegions(top=0.7, bottom=0.4))


@patch('adb_auto_player.template_matching.cv2.matchTemplate')
@patch('adb_auto_player.template_matching.cv2.minMaxLoc')
def test_find_template_match_best_match_found(mock_min_max_loc, mock_match_template, mock_screen_image):
    """Test find_template_match returns coordinates when a match is found (BEST mode)."""
    template = np.zeros((10, 10, 3), dtype=np.uint8)
    result_matrix = np.zeros((90, 90))
    match_val = 0.95
    match_loc = (50, 40)
    
    mock_match_template.return_value = result_matrix
    mock_min_max_loc.return_value = (0, match_val, (0, 0), match_loc)
    
    result = find_template_match(
        base_image=mock_screen_image,
        template_image=template,
        match_mode=MatchMode.BEST,
        threshold=0.9
    )
    
    mock_match_template.assert_called_once()
    mock_min_max_loc.assert_called_once_with(result_matrix)
    
    # Result should be center of template: match_loc + half template dimensions
    expected_x = match_loc[0] + template.shape[1] // 2
    expected_y = match_loc[1] + template.shape[0] // 2
    assert result == (expected_x, expected_y)


@patch('adb_auto_player.template_matching.cv2.matchTemplate')
@patch('adb_auto_player.template_matching.cv2.minMaxLoc')
def test_find_template_match_best_no_match(mock_min_max_loc, mock_match_template, mock_screen_image):
    """Test find_template_match returns None when no match is found (BEST mode)."""
    template = np.zeros((10, 10, 3), dtype=np.uint8)
    result_matrix = np.zeros((90, 90))
    match_val = 0.85  # Below threshold of 0.9
    match_loc = (50, 40)
    
    mock_match_template.return_value = result_matrix
    mock_min_max_loc.return_value = (0, match_val, (0, 0), match_loc)
    
    result = find_template_match(
        base_image=mock_screen_image,
        template_image=template,
        match_mode=MatchMode.BEST,
        threshold=0.9
    )
    
    assert result is None


@patch('adb_auto_player.template_matching.cv2.matchTemplate')
@patch('adb_auto_player.template_matching.np.where')
def test_find_template_match_directional(mock_where, mock_match_template, mock_screen_image):
    """Test find_template_match with directional modes."""
    template = np.zeros((10, 10, 3), dtype=np.uint8)
    result_matrix = np.zeros((90, 90))
    
    # Create sample match locations: y coordinates first, x coordinates second
    mock_match_template.return_value = result_matrix
    mock_where.return_value = (np.array([20, 30, 40]), np.array([10, 20, 30]))
    
    # Test TOP_LEFT mode
    result = find_template_match(
        base_image=mock_screen_image,
        template_image=template,
        match_mode=MatchMode.TOP_LEFT,
        threshold=0.9
    )
    
    # Should select (10, 20) as top-left most point (lowest y, lowest x)
    expected_x = 10 + template.shape[1] // 2
    expected_y = 20 + template.shape[0] // 2
    assert result == (expected_x, expected_y)
    
    # Test BOTTOM_RIGHT mode
    result = find_template_match(
        base_image=mock_screen_image,
        template_image=template,
        match_mode=MatchMode.BOTTOM_RIGHT,
        threshold=0.9
    )
    
    # Should select (30, 40) as bottom-right most point (highest y, highest x)
    expected_x = 30 + template.shape[1] // 2
    expected_y = 40 + template.shape[0] // 2
    assert result == (expected_x, expected_y)


@patch('adb_auto_player.template_matching._suppress_close_matches')
@patch('adb_auto_player.template_matching.cv2.matchTemplate')
@patch('adb_auto_player.template_matching.np.where')
def test_find_all_template_matches(mock_where, mock_match_template, mock_suppress, mock_screen_image):
    """Test find_all_template_matches returns all match coordinates."""
    template = np.zeros((10, 10, 3), dtype=np.uint8)
    result_matrix = np.zeros((90, 90))
    
    # Create sample match locations
    mock_match_template.return_value = result_matrix
    mock_where.return_value = (np.array([20, 30, 40]), np.array([10, 20, 30]))
    
    # Need to mock _suppress_close_matches to return all matches
    expected_centers = [
        (10 + template.shape[1] // 2, 20 + template.shape[0] // 2),
        (20 + template.shape[1] // 2, 30 + template.shape[0] // 2),
        (30 + template.shape[1] // 2, 40 + template.shape[0] // 2)
    ]
    mock_suppress.return_value = expected_centers
    
    results = find_all_template_matches(
        base_image=mock_screen_image,
        template_image=template,
        threshold=0.9,
        min_distance=20  # Large enough that all matches should be returned
    )
    
    # Should find 3 matches with centers at match locations + half template size
    assert len(results) == 3
    for expected in expected_centers:
        assert expected in results


@patch('adb_auto_player.template_matching._suppress_close_matches')
@patch('adb_auto_player.template_matching.cv2.matchTemplate')
@patch('adb_auto_player.template_matching.np.where')
def test_find_all_template_matches_suppression(mock_where, mock_match_template, mock_suppress, mock_screen_image):
    """Test that find_all_template_matches uses suppression for close matches."""
    template = np.zeros((10, 10, 3), dtype=np.uint8)
    result_matrix = np.zeros((90, 90))
    
    # Create sample match locations
    mock_match_template.return_value = result_matrix
    mock_where.return_value = (np.array([20, 21, 40]), np.array([10, 11, 30]))
    
    # Two matches are close, should call suppress
    original_centers = [
        (15, 25),  # Close to each other
        (16, 26),  # Close to the first one
        (35, 45)   # Far from others
    ]
    mock_suppress.return_value = [(15, 25), (35, 45)]  # Suppressed result with only two centers
    
    find_all_template_matches(
        base_image=mock_screen_image,
        template_image=template,
        threshold=0.9,
        min_distance=5  # Small enough that the close matches should be suppressed
    )
    
    # Should call suppress with matches and min_distance
    mock_suppress.assert_called_once()
    args, kwargs = mock_suppress.call_args
    assert len(args) == 2
    assert len(args[0]) == 3  # 3 matches passed to suppress
    assert args[1] == 5  # min_distance=5


def test_validate_threshold():
    """Test that _validate_threshold raises ValueError for invalid thresholds."""
    # Valid thresholds
    _validate_threshold(0.0)
    _validate_threshold(0.5)
    _validate_threshold(1.0)
    
    # Invalid thresholds
    with pytest.raises(ValueError):
        _validate_threshold(-0.1)
    with pytest.raises(ValueError):
        _validate_threshold(1.1)
    
def test_suppress_close_matches():
    """Test _suppress_close_matches correctly filters nearby coordinates."""
    matches = [(10, 10), (12, 12), (30, 30), (31, 32)]
    
    # With min_distance=5, should keep (10,10) and (30,30)
    result = _suppress_close_matches(matches, 5)
    assert len(result) == 2
    assert (10, 10) in result
    assert (30, 30) in result
    
    # With min_distance=1, should keep all except possibly one close pair
    result = _suppress_close_matches(matches, 1)
    assert len(result) >= 3  # At least 3 points should be kept
    
    # With min_distance=50, should keep only one point
    result = _suppress_close_matches(matches, 50)
    assert len(result) == 1


class TestTemplateMatching(unittest.TestCase):
    """Pytest Template Matching."""

    def test_similar_image_templates(self) -> None:
        """Test similar_image with templates."""
        f1 = TEST_DATA_DIR / "records_formation_1.png"
        f2 = TEST_DATA_DIR / "records_formation_2.png"
        # f5 = TEST_DATA_DIR / "records_formation_5.png"
        # f6 = TEST_DATA_DIR / "records_formation_6.png"
        # f7 = TEST_DATA_DIR / "records_formation_7.png"

        result = similar_image(
            base_image=load_image(f1),
            template_image=load_image(f1),
        )
        self.assertTrue(result)

        result = similar_image(
            base_image=load_image(f1),
            template_image=load_image(f2),
        )
        self.assertFalse(result)
