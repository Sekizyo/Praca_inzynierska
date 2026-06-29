import pytest
import taichi as ti
from taichi import Vector, Field, MatrixField
from modules.voronoi import VoronoiDiagram

def test_voronoi_logic():
    # Setup test data
    voronoi = VoronoiDiagram(boundary=100.0, resolution=10)
    
    player_count = 1
    enemy_count = 1
    
    player_pos = Vector.field(3, dtype=ti.f32, shape=player_count)
    player_health = Vector.field(1, dtype=ti.f32, shape=player_count)
    
    enemy_pos = Vector.field(3, dtype=ti.f32, shape=enemy_count)
    enemy_health = Vector.field(1, dtype=ti.f32, shape=enemy_count)
    
    # Player at one side, enemy at the other
    player_pos[0] = [50.0, 50.0, 0.0]
    player_health[0] = [100.0]
    
    enemy_pos[0] = [-50.0, -50.0, 0.0]
    enemy_health[0] = [100.0]
    
    voronoi.update(player_pos, player_count, player_health, enemy_pos, enemy_count, enemy_health)
    voronoi.pull_stats()
    
    # They should have roughly 50% territory
    ratio = voronoi.get_territory_ratio()
    assert 40.0 < ratio < 60.0
    
    # Now kill enemy
    enemy_health[0] = [0.0]
    voronoi.update(player_pos, player_count, player_health, enemy_pos, enemy_count, enemy_health)
    voronoi.pull_stats()
    
    ratio = voronoi.get_territory_ratio()
    assert ratio == 100.0
