import pytest
import taichi as ti
from modules.swarms import Swarms
from modules.gui_utils import GamePresets

@pytest.fixture
def test_presets():
    presets = GamePresets()
    presets.attacking_drone_count = 1
    presets.defending_drone_count = 1
    presets.map_size = 1000
    presets.fog_of_war = True
    presets.fog_of_war_radius = 1
    presets.attacking_path_normalized = [(500.0, 500.0, 500.0, None)]
    presets.ai_path_normalized = [(500.0, 500.0, 500.0, None)]
    return presets

from unittest.mock import MagicMock

def test_fog_of_war_radius(test_presets):
    mock_stats = MagicMock()
    swarms = Swarms(mock_stats, test_presets)
    
    # We will manually populate the grids to test the visibility logic
    # Player at grid cell (5, 5, 5)
    swarms.grid_count_p[5, 5, 5] = 1
    swarms.grid_buckets_p[5, 5, 5, 0] = 0 # Player index 0
    
    # Enemy at grid cell (5, 5, 5) - Same cell
    swarms.grid_count_e[5, 5, 5] = 1
    
    swarms.gamePreset.fog_of_war_radius = 0
    swarms.update_visibility(True)
    assert swarms.attacking_swarm.visible[0][0] == 1, "Player should be visible when in same cell"
    
    # Move enemy to adjacent cell (6, 5, 5)
    swarms.grid_count_e[5, 5, 5] = 0
    swarms.grid_count_e[6, 5, 5] = 1
    
    swarms.gamePreset.fog_of_war_radius = 0
    swarms.update_visibility(True)
    assert swarms.attacking_swarm.visible[0][0] == 0, "Player should NOT be visible with radius 0"
    
    swarms.gamePreset.fog_of_war_radius = 1
    swarms.update_visibility(True)
    assert swarms.attacking_swarm.visible[0][0] == 1, "Player should be visible with radius 1"
    
    # Move enemy two cells away (7, 5, 5)
    swarms.grid_count_e[6, 5, 5] = 0
    swarms.grid_count_e[7, 5, 5] = 1
    
    swarms.gamePreset.fog_of_war_radius = 1
    swarms.update_visibility(True)
    assert swarms.attacking_swarm.visible[0][0] == 0, "Player should NOT be visible with radius 1 two cells away"
    
    swarms.gamePreset.fog_of_war_radius = 2
    swarms.update_visibility(True)
    assert swarms.attacking_swarm.visible[0][0] == 1, "Player should be visible with radius 2 two cells away"
