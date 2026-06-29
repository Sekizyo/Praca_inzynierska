import pytest
import taichi as ti
from modules.drone import DroneSwarm
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

def test_drone_swarm_initialization(test_presets):
    swarm = DroneSwarm(test_presets, team=0)
    
    assert swarm.N == 10
    assert swarm.team == 0
    
    swarm.update_statistics(0)
    swarm.get_stats()
    assert swarm.get_alive_count() == 10
    
    pos = swarm.get_pos_field().to_numpy()
    assert len(pos) == 10
    
def test_drone_swarm_movement(test_presets):
    swarm = DroneSwarm(test_presets, team=0)
    
    # Fake grid data required for update method
    grid_shape = ti.Vector([10, 10, 10])
    grid_count = ti.field(dtype=ti.i32, shape=grid_shape)
    grid_buckets = ti.field(dtype=ti.i32, shape=(10, 10, 10, 300))
    grid_cell_size = 128.0
    grid_padding = 1
    grid_offset = ti.Vector([1000.0, 1000.0, 0.0])
    
    # Set target
    swarm.set_target(500.0, 500.0, 500.0)
    
    initial_center = swarm.get_swarm_center()
    
    # Run a few updates
    for _ in range(10):
        swarm.update(0.1, grid_count, grid_buckets, grid_cell_size, grid_shape, grid_padding, grid_offset)
        swarm.update_statistics(0)
    
    new_center = swarm.get_swarm_center()
    
    # Should have moved
    assert initial_center != new_center
