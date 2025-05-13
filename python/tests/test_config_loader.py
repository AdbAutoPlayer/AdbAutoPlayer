import pytest
import tomllib
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, PropertyMock

# Import the actual class to be tested
from adb_auto_player.config_loader import ConfigLoader

# --- Fixtures ---

@pytest.fixture(autouse=True)
def reset_config_loader_singleton():
    """Reset the ConfigLoader singleton before each test."""
    ConfigLoader._instance = None
    # Ensure attributes are reset if they were somehow set outside __init__
    if hasattr(ConfigLoader, '_working_dir'):
        delattr(ConfigLoader, '_working_dir')
    if hasattr(ConfigLoader, '_games_dir'):
        delattr(ConfigLoader, '_games_dir')
    if hasattr(ConfigLoader, '_main_config'):
        delattr(ConfigLoader, '_main_config')
    yield # Run the test
    # Clean up after test if necessary, though resetting before is usually sufficient
    ConfigLoader._instance = None

@pytest.fixture
def mock_cwd():
    """Provides a mock Path object for Path.cwd()."""
    return MagicMock(spec=Path)

# --- Test Cases ---

def test_singleton_instance():
    """Test that ConfigLoader returns the same instance."""
    instance1 = ConfigLoader()
    instance2 = ConfigLoader()
    assert instance1 is instance2

@patch('adb_auto_player.config_loader.Path.cwd')
def test_working_dir_property(mock_path_cwd, mock_cwd):
    """Test the working_dir property returns the result of Path.cwd()."""
    mock_path_cwd.return_value = mock_cwd
    loader = ConfigLoader()
    assert loader.working_dir == mock_cwd
    mock_path_cwd.assert_called_once()

@patch('adb_auto_player.config_loader.Path.cwd')
def test_games_dir_finds_in_working_dir(mock_path_cwd):
    """Test games_dir finds 'games' directly in working_dir (GUI context)."""
    mock_cwd = MagicMock(spec=Path)
    mock_path_cwd.return_value = mock_cwd
    mock_games_path = MagicMock(spec=Path)
    mock_cwd.__truediv__.return_value = mock_games_path # Mock '/' operator
    mock_games_path.exists.return_value = True
    # Mock other candidates to not exist
    mock_cwd.parent = MagicMock(spec=Path)
    mock_cwd.parent.__truediv__().exists.return_value = False
    mock_cwd.__truediv__().__truediv__().exists.return_value = False # for adb_auto_player/games
    mock_cwd.parent.parent = MagicMock(spec=Path)
    mock_cwd.parent.parent.__truediv__().__truediv__().__truediv__().__truediv__().exists.return_value = False # dev structure

    loader = ConfigLoader()
    # Check the final result instead of specific call count
    assert loader.games_dir == mock_games_path
    # Verify the correct path was checked and found
    mock_cwd.__truediv__.assert_any_call("games")
    mock_games_path.exists.assert_called_once()

@patch('adb_auto_player.config_loader.Path.cwd')
def test_games_dir_finds_in_parent_dir(mock_path_cwd, mock_cwd):
    """Test games_dir finds 'games' in parent of working_dir (CLI context)."""
    mock_path_cwd.return_value = mock_cwd
    mock_parent_path = MagicMock(spec=Path)
    mock_cwd.parent = mock_parent_path

    mock_games_path_cwd = MagicMock(spec=Path)
    mock_games_path_parent = MagicMock(spec=Path)

    # Simulate paths and existence checks
    def truediv_side_effect(arg):
        if arg == "games": return mock_games_path_cwd
        return MagicMock() # Default for other divisions
    mock_cwd.__truediv__.side_effect = truediv_side_effect
    mock_parent_path.__truediv__.return_value = mock_games_path_parent

    mock_games_path_cwd.exists.return_value = False # Not in cwd/games
    mock_games_path_parent.exists.return_value = True # Found in parent/games

    loader = ConfigLoader()
    assert loader.games_dir == mock_games_path_parent

    # Check calls
    assert mock_cwd.__truediv__.call_count >= 1 # Called for cwd/games
    mock_games_path_cwd.exists.assert_called_once()
    mock_parent_path.__truediv__.assert_called_once_with("games")
    mock_games_path_parent.exists.assert_called_once()

@patch('adb_auto_player.config_loader.Path.cwd')
def test_games_dir_finds_in_dev_structure(mock_path_cwd):
    """Test games_dir finds 'games' in development structure."""
    mock_cwd = MagicMock(spec=Path, name="cwd()") # e.g., /project/python/tests
    mock_path_cwd.return_value = mock_cwd
    mock_parent1 = MagicMock(spec=Path, name="cwd().parent") # /project/python
    mock_parent2 = MagicMock(spec=Path, name="cwd().parent.parent") # /project
    mock_cwd.parent = mock_parent1
    mock_parent1.parent = mock_parent2

    mock_python_dir = MagicMock(spec=Path, name="project/python")
    mock_adb_player_dir = MagicMock(spec=Path, name="project/python/adb_auto_player")
    mock_games_dir_dev = MagicMock(spec=Path, name="project/python/adb_auto_player/games")

    # Mock path construction for candidate 4
    mock_parent2.__truediv__.return_value = mock_python_dir
    mock_python_dir.__truediv__.return_value = mock_adb_player_dir
    mock_adb_player_dir.__truediv__.return_value = mock_games_dir_dev

    # Simulate existence checks failing for other candidates
    mock_cwd.__truediv__().exists.return_value = False # candidate 1: cwd / games
    mock_parent1.__truediv__().exists.return_value = False # candidate 2: cwd.parent / games
    # Correctly mock candidate 3 check: cwd / "adb_auto_player" / "games"
    mock_cwd_adb_player_games = MagicMock(spec=Path)
    mock_cwd_adb_player = MagicMock(spec=Path)
    mock_cwd.__truediv__.side_effect = lambda x: mock_cwd_adb_player if x == "adb_auto_player" else MagicMock(exists=lambda: False)
    mock_cwd_adb_player.__truediv__.return_value = mock_cwd_adb_player_games
    mock_cwd_adb_player_games.exists.return_value = False # candidate 3 fails

    # The target dev path exists (candidate 4)
    mock_games_dir_dev.exists.return_value = True

    loader = ConfigLoader()

    assert loader.games_dir == mock_games_dir_dev
    # Check that the dev path was indeed constructed and checked
    mock_parent2.__truediv__.assert_called_with("python")
    mock_python_dir.__truediv__.assert_called_with("adb_auto_player")
    mock_adb_player_dir.__truediv__.assert_called_with("games")
    mock_games_dir_dev.exists.assert_called_once()

@patch('adb_auto_player.config_loader.Path.cwd')
def test_games_dir_uses_first_candidate_if_none_exist(mock_path_cwd):
    """Test games_dir returns the first candidate checked if none actually exist."""
    mock_cwd = MagicMock(spec=Path, name="cwd")
    mock_path_cwd.return_value = mock_cwd

    # Define distinct mock objects for each potential final path
    expected_games_dir_path = MagicMock(
        spec=Path, name="expected_games_dir_path_from_cand0"
    )
    expected_games_dir_path.exists.return_value = False

    mock_cand1_path = MagicMock(spec=Path, name="mock_cand1_path")
    mock_cand1_path.exists.return_value = False

    mock_cand2_path = MagicMock(spec=Path, name="mock_cand2_path")
    mock_cand2_path.exists.return_value = False

    mock_cand3_path = MagicMock(spec=Path, name="mock_cand3_path")
    mock_cand3_path.exists.return_value = False

    # Mock intermediate path objects
    mock_cwd_parent = MagicMock(spec=Path, name="cwd_parent")
    mock_cwd.parent = mock_cwd_parent

    mock_cwd_parent_parent = MagicMock(spec=Path, name="cwd_parent_parent")
    mock_cwd.parent.parent = mock_cwd_parent_parent

    mock_cwd_div_adb_auto_player = MagicMock(
        spec=Path, name="cwd_div_adb_auto_player"
    )
    mock_cwd_parent_parent_div_python = MagicMock(
        spec=Path, name="cwd_parent_parent_div_python"
    )
    mock_intermediate_cand3_div_adb = MagicMock(
        spec=Path, name="intermediate_cand3_div_adb"
    )

    # Configure side effects for __truediv__
    def cwd_truediv_side_effect(segment):
        if segment == "games":  # For candidates[0]
            return expected_games_dir_path
        elif segment == "adb_auto_player":  # For candidates[2] intermediate
            return mock_cwd_div_adb_auto_player
        return MagicMock(name=f"unexpected_cwd_truediv_{segment}")
    mock_cwd.__truediv__.side_effect = cwd_truediv_side_effect
    # Completes candidates[2]
    mock_cwd_div_adb_auto_player.__truediv__.return_value = mock_cand2_path

    # For candidates[1] (cwd.parent / "games")
    mock_cwd_parent.__truediv__.return_value = mock_cand1_path

    def cwd_parent_parent_truediv_side_effect(segment):
        if segment == "python":  # For candidates[3] intermediate
            return mock_cwd_parent_parent_div_python
        return MagicMock(name=f"unexpected_cwd_parent_parent_truediv_{segment}")
    mock_cwd_parent_parent.__truediv__.side_effect = (
        cwd_parent_parent_truediv_side_effect
    )
    
    def intermediate_cand3_truediv_effect(segment):
        if segment == "adb_auto_player":
            return mock_intermediate_cand3_div_adb
        return MagicMock(name=f"unexpected_intermediate_truediv_{segment}")
    mock_cwd_parent_parent_div_python.__truediv__.side_effect = (
        intermediate_cand3_truediv_effect
    )
    # Completes candidates[3]
    mock_intermediate_cand3_div_adb.__truediv__.return_value = mock_cand3_path
    
    ConfigLoader._instance = None # Reset singleton for clean test
    loader = ConfigLoader()
    loader._games_dir = None  # Force re-evaluation

    assert loader.games_dir == expected_games_dir_path

@patch('builtins.open', side_effect=FileNotFoundError("Simulated file not found"))
@patch('adb_auto_player.config_loader.logging')
@patch.object(Path, 'cwd')
def test_main_config_not_found(
    mock_path_cwd_method,  # Mock for Path.cwd
    mock_logging,
    mock_builtin_open,
    mock_cwd  # Injected fixture
):
    """Test main_config returns empty dict and logs if config.toml not found."""
    mock_path_cwd_method.return_value = mock_cwd # Use the new name for the mock method

    with patch.object(Path, 'exists', return_value=False):
        loader = ConfigLoader()
        loader._main_config = None # Force re-evaluation
        config = loader.main_config
        assert config == {}
        mock_logging.debug.assert_any_call(
            "Failed to load main config: Simulated file not found"
        )
        mock_logging.debug.assert_any_call("Using default main config values")
