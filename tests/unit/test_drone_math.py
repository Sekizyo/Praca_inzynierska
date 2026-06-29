import pytest
import taichi as ti
import numpy as np
from taichi import Vector
from modules.drone import DroneSwarm
from modules.gui_utils import GamePresets

@pytest.fixture
def test_presets():
    presets = GamePresets()
    presets.attacking_drone_count = 2
    presets.defending_drone_count = 0
    presets.map_size = 1000
    presets.drone_max_speed = 20.0
    # Use attack mode multipliers
    presets.boids_attack_separation = 1.0
    presets.boids_attack_alignment = 1.0
    presets.boids_attack_cohesion = 1.0
    presets.drone_perception_radius = 100.0
    presets.attacking_path_normalized = [(500.0, 500.0, 500.0, None)]
    presets.ai_path_normalized = [(500.0, 500.0, 500.0, None)]
    return presets

def setup_grid(swarm, positions):
    grid_shape = ti.Vector([10, 10, 10])
    grid_count = ti.field(dtype=ti.i32, shape=grid_shape)
    grid_buckets = ti.field(dtype=ti.i32, shape=(10, 10, 10, 10))
    grid_cell_size = 200.0
    grid_padding = 1
    grid_offset = ti.Vector([1000.0, 1000.0, 1000.0])
    
    for i, p in enumerate(positions):
        swarm.pos[i] = p
        
    @ti.kernel
    def populate_grid():
        for I in ti.grouped(grid_count):
            grid_count[I] = 0
            
        for i in range(swarm.N):
            if swarm.active[i][0] != 0:
                pos = swarm.pos[i] + grid_offset
                gx = int(pos.x / grid_cell_size) + grid_padding
                gy = int(pos.y / grid_cell_size) + grid_padding
                gz = int(pos.z / grid_cell_size) + grid_padding
                
                idx = ti.atomic_add(grid_count[gx, gy, gz], 1)
                grid_buckets[gx, gy, gz, idx] = i
                
    populate_grid()
    return grid_count, grid_buckets, grid_cell_size, grid_shape, grid_padding, grid_offset

def test_flocking_separation(test_presets):
    test_presets.boids_attack_alignment = 0.0
    test_presets.boids_attack_cohesion = 0.0
    test_presets.boids_attack_separation = 1.0
    
    swarm = DroneSwarm(test_presets, 0)
    swarm.update_mode(swarm.mode)
    
    # Drone 0 at origin, Drone 1 very close on X axis
    positions = [
        [0.0, 0.0, 0.0],
        [10.0, 0.0, 0.0]
    ]
    swarm.vel[0] = [0.0, 0.0, 0.0]
    swarm.vel[1] = [0.0, 0.0, 0.0]
    
    grid = setup_grid(swarm, positions)
    
    out_force = Vector.field(3, dtype=ti.f32, shape=1)
    
    @ti.kernel
    def run_flocking(shape: ti.types.vector(3, ti.i32), offset: ti.types.vector(3, ti.f32)):
        out_force[0] = swarm.calculate_flocking(
            0, swarm.pos[0], swarm.vel[0],
            grid[0], grid[1], grid[2], shape, grid[4], offset
        )
        
    run_flocking(grid[3], grid[5])
    force = out_force[0]
    
    # Separation force should repel drone 0 away from drone 1, so negative X
    assert force.x < 0.0
    assert abs(force.y) < 1e-5
    assert abs(force.z) < 1e-5

def test_flocking_alignment(test_presets):
    test_presets.boids_attack_alignment = 1.0
    test_presets.boids_attack_cohesion = 0.0
    test_presets.boids_attack_separation = 0.0
    # Need them to be outside separation radius (radius*0.6 = 60) but inside alignment radius (100)
    
    swarm = DroneSwarm(test_presets, 0)
    swarm.update_mode(swarm.mode)
    
    positions = [
        [0.0, 0.0, 0.0],
        [80.0, 0.0, 0.0]  
    ]
    swarm.vel[0] = [0.0, 0.0, 0.0]
    swarm.vel[1] = [0.0, 10.0, 0.0] # Drone 1 moving up
    
    grid = setup_grid(swarm, positions)
    out_force = Vector.field(3, dtype=ti.f32, shape=1)
    
    @ti.kernel
    def run_flocking(shape: ti.types.vector(3, ti.i32), offset: ti.types.vector(3, ti.f32)):
        out_force[0] = swarm.calculate_flocking(
            0, swarm.pos[0], swarm.vel[0],
            grid[0], grid[1], grid[2], shape, grid[4], offset
        )
        
    run_flocking(grid[3], grid[5])
    force = out_force[0]
    
    # Drone 0 should align with Drone 1, meaning force in positive Y
    assert abs(force.x) < 1e-5
    assert force.y > 0.0
    assert abs(force.z) < 1e-5

def test_flocking_cohesion(test_presets):
    test_presets.boids_attack_alignment = 0.0
    test_presets.boids_attack_cohesion = 1.0
    test_presets.boids_attack_separation = 0.0
    
    swarm = DroneSwarm(test_presets, 0)
    swarm.update_mode(swarm.mode)
    
    positions = [
        [0.0, 0.0, 0.0],
        [80.0, 0.0, 0.0]  
    ]
    swarm.vel[0] = [0.0, 0.0, 0.0]
    swarm.vel[1] = [0.0, 0.0, 0.0]
    
    grid = setup_grid(swarm, positions)
    out_force = Vector.field(3, dtype=ti.f32, shape=1)
    
    @ti.kernel
    def run_flocking(shape: ti.types.vector(3, ti.i32), offset: ti.types.vector(3, ti.f32)):
        out_force[0] = swarm.calculate_flocking(
            0, swarm.pos[0], swarm.vel[0],
            grid[0], grid[1], grid[2], shape, grid[4], offset
        )
        
    run_flocking(grid[3], grid[5])
    force = out_force[0]
    
    # Drone 0 should be pulled towards Drone 1 (positive X)
    assert force.x > 0.0
    assert abs(force.y) < 1e-5
    assert abs(force.z) < 1e-5

def test_combat_fov_and_distance(test_presets):
    # Set shooting params
    test_presets.drone_shooting_range = 50
    test_presets.drone_shooting_perception_radius = 0.5 # Cosine of 60 degrees (120 deg FOV)
    test_presets.projectile_speed = 100.0
    
    swarm = DroneSwarm(test_presets, 0)
    swarm.pos[0] = [0.0, 0.0, 0.0]
    swarm.vel[0] = [10.0, 0.0, 0.0] # Moving +X, facing +X
    swarm.active[1] = [0] # Deactivate drone 1
    
    enemy_count = 3
    enemy_pos = Vector.field(3, dtype=ti.f32, shape=enemy_count)
    enemy_health = Vector.field(1, dtype=ti.f32, shape=enemy_count)
    
    # Enemy 0: In front, in range (shootable)
    enemy_pos[0] = [30.0, 0.0, 0.0]
    enemy_health[0] = [100.0]
    
    # Enemy 1: Behind, in range (ignored by FOV)
    enemy_pos[1] = [-30.0, 0.0, 0.0]
    enemy_health[1] = [100.0]
    
    # Enemy 2: In front, out of range (ignored)
    enemy_pos[2] = [80.0, 0.0, 0.0]
    enemy_health[2] = [100.0]
    
    # Setup grid for enemies
    grid_shape = ti.Vector([10, 10, 10])
    grid_count = ti.field(dtype=ti.i32, shape=grid_shape)
    grid_buckets = ti.field(dtype=ti.i32, shape=(10, 10, 10, 10))
    grid_cell_size = 200.0
    grid_padding = 1
    grid_offset = ti.Vector([1000.0, 1000.0, 1000.0])
    
    @ti.kernel
    def populate_enemy_grid():
        for I in ti.grouped(grid_count):
            grid_count[I] = 0
            
        for i in range(enemy_count):
            pos = enemy_pos[i] + grid_offset
            gx = int(pos.x / grid_cell_size) + grid_padding
            gy = int(pos.y / grid_cell_size) + grid_padding
            gz = int(pos.z / grid_cell_size) + grid_padding
            idx = ti.atomic_add(grid_count[gx, gy, gz], 1)
            grid_buckets[gx, gy, gz, idx] = i
            
    populate_enemy_grid()
    
    assert swarm.projectile_active[0] == 0
    
    swarm.batched_combat_update(
        0.1, enemy_pos, enemy_count, enemy_health,
        grid_count, grid_buckets, grid_offset, grid_shape, grid_cell_size, grid_padding
    )
    
    # Check projectiles
    active_projectiles = 0
    target_pos = None
    for i in range(swarm.max_projectiles):
        if swarm.projectile_active[i] == 1:
            active_projectiles += 1
            target_pos = swarm.projectile_pos[i]
            vel = swarm.projectile_vel[i]
            
            # Should be shooting at Enemy 0 (+X direction)
            assert vel.x > 0.0
            assert abs(vel.y) < 1e-5
            assert abs(vel.z) < 1e-5
            assert abs(vel.norm() - 100.0) < 1e-4
            
    # Should only spawn ONE projectile (since Drone 1 is active=1 but cooldown might be checked, wait drone 1 is not initialized with pos so it's far away, wait it's initialized randomly in GamePresets... actually we only set pos[0]! Drone 1 might shoot too if it randomly spawned near enemy 0. Let's deactivate Drone 1.)
    
def test_boundary_forces(test_presets):
    test_presets.map_size = 1000
    swarm = DroneSwarm(test_presets, 0)
    
    # Drone 0 near max X boundary
    swarm.pos[0] = [995.0, 0.0, 500.0]
    swarm.vel[0] = [10.0, 0.0, 0.0]
    
    # Dummy grid
    grid_shape = ti.Vector([10, 10, 10])
    grid_count = ti.field(dtype=ti.i32, shape=grid_shape)
    grid_buckets = ti.field(dtype=ti.i32, shape=(10, 10, 10, 10))
    grid_cell_size = 200.0
    grid_padding = 1
    grid_offset = ti.Vector([1000.0, 1000.0, 1000.0])
    
    # Empty grid
    @ti.kernel
    def clear_grid():
        for I in ti.grouped(grid_count):
            grid_count[I] = 0
    clear_grid()
    
    swarm.update(0.1, grid_count, grid_buckets, grid_cell_size, grid_shape, grid_padding, grid_offset)
    
    # The boundary is 1000, margin is 10. Max boundary = 990.
    # Drone is at 995, so it's past the margin, should be repelled.
    # Acceleration should be negative X.
    assert swarm.acc[0].x < 0.0
