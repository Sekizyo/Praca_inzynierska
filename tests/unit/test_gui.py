import pytest
from unittest.mock import MagicMock
from modules.gui import GUI
from modules.gui_utils import GamePresets

@pytest.fixture
def test_presets():
    presets = GamePresets()
    presets.attacking_drone_count = 10
    presets.defending_drone_count = 10
    presets.map_size = 1000
    presets.attacking_path_normalized = [(100, 100, 100, None)]
    presets.ai_path_normalized = [(-100, -100, 100, None)]
    return presets

def test_gui_initialization(test_presets):
    mock_gui = MagicMock()
    mock_window = MagicMock()
    mock_scene = MagicMock()
    
    gui = GUI(mock_gui, mock_window, mock_scene, test_presets)
    assert not gui.victory
    assert not gui.defeat
    assert gui.domination == 0.5
    
    loader = gui.load()
    steps = list(loader)
    
    assert len(steps) > 0
    assert hasattr(gui, "swarms")
    assert hasattr(gui, "map")
    assert hasattr(gui, "voronoi")
