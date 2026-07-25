import pytest
import taichi as ti
import numpy as np
from taichi import Vector
from modules.drone import DroneSwarm
from modules.gui_utils import GamePresets

@pytest.fixture
def test_presets_obstacles():
    presets = GamePresets()
    presets.attacking_drone_count = 1
    presets.defending_drone_count = 0
    presets.map_size = 1000
    presets.drone_max_speed = 20.0
    presets.drone_perception_radius = 100.0
    presets.attacking_path_normalized = [(500.0, 500.0, 500.0, None)]
    presets.ai_path_normalized = [(500.0, 500.0, 500.0, None)]
    return presets

def setup_empty_grid():
    grid_shape = ti.Vector([10, 10, 10])
    grid_count = ti.field(dtype=ti.i32, shape=grid_shape)
    grid_buckets = ti.field(dtype=ti.i32, shape=(10, 10, 10, 10))
    grid_cell_size = 200.0
    grid_padding = 1
    grid_offset = ti.Vector([1000.0, 1000.0, 1000.0])
    
    @ti.kernel
    def clear_grid():
        for I in ti.grouped(grid_count):
            grid_count[I] = 0
            
    clear_grid()
    return grid_count, grid_buckets, grid_cell_size, grid_shape, grid_padding, grid_offset

def test_obstacle_avoidance(test_presets_obstacles):
    swarm = DroneSwarm(test_presets_obstacles, 0)
    
    # Drone moving in +X direction, slightly offset in Y
    swarm.pos[0] = [0.0, 5.0, 500.0]
    swarm.vel[0] = [10.0, 0.0, 0.0]
    swarm.acc[0] = [0.0, 0.0, 0.0]
    
    # Set up 1 obstacle directly in front but centered at Y=0
    obstacle_count = 1
    obstacle_pos = ti.Vector.field(3, dtype=ti.f32, shape=1)
    obstacle_radius = ti.field(dtype=ti.f32, shape=1)
    
    obstacle_pos[0] = [50.0, 0.0, 500.0]
    obstacle_radius[0] = 20.0
    
    grid = setup_empty_grid()
    
    swarm.update(
        0.1, 
        grid[0], grid[1], grid[2], grid[3], grid[4], grid[5],
        obstacle_pos, obstacle_radius, obstacle_count
    )
    
    # Avoidance should push the drone in -X (away from obstacle) and +Y (since drone is at Y=5 and obstacle is at Y=0)
    acc = swarm.acc[0]
    assert acc.x < 0.0, f"Expected negative X acceleration, got {acc.x}"
    assert acc.y > 0.0, f"Expected positive Y acceleration, got {acc.y}"


def test_projectile_obstacle_collision(test_presets_obstacles):
    test_presets_obstacles.projectile_max_lifetime = 5.0
    swarm = DroneSwarm(test_presets_obstacles, 0)
    
    # Deactivate drone so it doesn't do anything
    swarm.active[0] = [0]
    
    # Manually spawn a projectile
    swarm.projectile_active[0] = 1
    swarm.projectile_pos[0] = [40.0, 0.0, 500.0]
    swarm.projectile_vel[0] = [100.0, 0.0, 0.0] # Moving +X fast
    swarm.projectile_lifetime[0] = 5.0
    swarm.projectile_free_count[None] -= 1
    
    # Set up obstacle at X=50
    obstacle_count = 1
    obstacle_pos = ti.Vector.field(3, dtype=ti.f32, shape=1)
    obstacle_radius = ti.field(dtype=ti.f32, shape=1)
    
    obstacle_pos[0] = [50.0, 0.0, 500.0]
    obstacle_radius[0] = 10.0
    
    # Dummy enemy fields
    enemy_pos = ti.Vector.field(3, dtype=ti.f32, shape=1)
    enemy_count = 0
    enemy_health = ti.Vector.field(1, dtype=ti.f32, shape=1)
    
    grid = setup_empty_grid()
    
    # Before update, projectile is active
    assert swarm.projectile_active[0] == 1
    
    swarm.batched_combat_update(
        0.1, # dt = 0.1, dx = 10.0 -> new pos = [50.0, 0.0, 500.0]
        enemy_pos, enemy_count, enemy_health,
        grid[0], grid[1], grid[5], grid[3], grid[2], grid[4],
        obstacle_pos, obstacle_radius, obstacle_count
    )
    
    # Projectile should have hit the obstacle and deactivated
    assert swarm.projectile_active[0] == 0
    
    # Verify free list was updated
    free_count = swarm.projectile_free_count[None]
    assert free_count == swarm.max_projectiles # Back to full capacity
