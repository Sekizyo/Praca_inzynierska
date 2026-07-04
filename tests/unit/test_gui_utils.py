import pytest
from modules.gui_utils import GuiState, GamePresets
from modules.drone import DroneModes

def test_gui_state_init():
    state = GuiState()
    assert state.PAUSED is False
    assert state.SHOW_VORONOI is False
    assert state.SHOW_BOUNDARY is True

def test_game_presets_init():
    presets = GamePresets()
    assert presets.map_size == 500
    assert presets.attacking_drone_count == 1000
    assert presets.fog_of_war is False

def test_normalize_to_world_coordinates():
    presets = GamePresets()
    presets.map_size = 100
    
    # Empty case
    assert presets.normalize_to_world_coordinates([]) == []
    
    # 3-tuple points
    points_3 = [(0.5, 0.5, 0.5), (-0.1, 0.0, 1.0)]
    normalized_3 = presets.normalize_to_world_coordinates(points_3)
    assert len(normalized_3) == 2
    assert normalized_3[0] == (50.0, 50.0, 50.0, None)
    assert normalized_3[1] == (-10.0, 0.0, 100.0, None)
    
    # 4-tuple points
    points_4 = [(0.5, 0.5, 0.5, DroneModes.ATTACK)]
    normalized_4 = presets.normalize_to_world_coordinates(points_4)
    assert len(normalized_4) == 1
    assert normalized_4[0] == (50.0, 50.0, 50.0, DroneModes.ATTACK)

def test_compare():
    presets1 = GamePresets()
    presets2 = GamePresets()
    
    assert presets1.compare(presets2) is True
    
    presets2.attacking_drone_count = 500
    assert presets1.compare(presets2) is False
    
    presets2.attacking_drone_count = 1000
    presets2.defending_drone_count = 500
    assert presets1.compare(presets2) is False

def test_generate_config_dict():
    presets = GamePresets()
    config_dict = presets.generate_config_dict()
    
    assert "map_size" in config_dict
    assert config_dict["map_size"][0] == 500
    assert "Type: int" in config_dict["map_size"][1]
    
    assert "fog_of_war" in config_dict
    assert config_dict["fog_of_war"][0] is False

def test_load_config():
    presets = GamePresets()
    original_size = presets.map_size
    
    # Load empty
    presets.load_config(None)
    assert presets.map_size == original_size
    
    presets.load_config({})
    assert presets.map_size == original_size
    
    # Load new values
    new_config = {
        "map_size": 800,
        "fog_of_war": True,
        "fog_of_war_radius": 2,
        "ai_agression_threshold": "0.855",
        "drone_path": [(0.1, 0.1, 0.1)]
    }
    presets.load_config(new_config)
    
    assert presets.map_size == 800
    assert presets.fog_of_war is True
    assert presets.fog_of_war_radius == 2
    assert presets.ai_agression_threshold == 0.85  # Python rounds 0.855 to 0.85
    
    assert len(presets.attacking_path) == 1
    # Check if normalized was updated
    assert len(presets.attacking_path_normalized) == 1
    assert presets.attacking_path_normalized[0] == (80.0, 80.0, 80.0, None) # 0.1 * 800
