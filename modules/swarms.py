import math
from modules.drone import DroneSwarm
from modules.colors import *
import taichi as ti
from taichi.ui.scene import SceneV2

from modules.gui_utils import GamePresets
from modules.enemy_ai import DefendingAI

@ti.data_oriented
class Swarms():
    def __init__(self, scene: SceneV2, gamePreset: GamePresets) -> None:
        self.gamePreset = gamePreset
        self.scene = scene
        self.map_size = gamePreset.map_size
        
        self.attacking_swarm = DroneSwarm(gamePreset, team=0)
        self.defending_swarm = DroneSwarm(gamePreset, team=1)
        self.defending_ai = DefendingAI(self.defending_swarm, gamePreset)
        self._init_swarms()
        
    def _init_swarms(self) -> None:
        self.total_drones = self.gamePreset.attacking_drone_count + self.gamePreset.defending_drone_count
        self.total_projectiles = self.total_drones * 2
        self.batched_drone_pos = ti.Vector.field(3, dtype=ti.f32, shape=self.total_drones)
        self.batched_projectile_pos = ti.Vector.field(3, dtype=ti.f32, shape=self.total_projectiles)
        
        self.frame_count = 0
        self.grid_cell_size = 64
        self.grid_padding = 2
        self.max_cell_capacity = 300
        
        grid_dim = int(self.map_size * 2 / self.grid_cell_size) + 2 * self.grid_padding
        self.grid_shape = ti.Vector([grid_dim, grid_dim, grid_dim])
        self.grid_offset = ti.Vector([self.map_size, self.map_size, 0.0])
        
        self.grid_count_p = ti.field(dtype=ti.i32, shape=self.grid_shape)
        self.grid_buckets_p = ti.field(dtype=ti.i32, shape=(self.grid_shape[0], self.grid_shape[1], self.grid_shape[2], self.max_cell_capacity))
        self.grid_count_e = ti.field(dtype=ti.i32, shape=self.grid_shape)
        self.grid_buckets_e = ti.field(dtype=ti.i32, shape=(self.grid_shape[0], self.grid_shape[1], self.grid_shape[2], self.max_cell_capacity))
        

    @ti.kernel
    def update_shared_grid(self):
        for I in ti.grouped(self.grid_count_p):
            self.grid_count_p[I] = 0
            self.grid_count_e[I] = 0
            
        for i in range(self.attacking_swarm.N):
            if self.attacking_swarm.active[i][0] != 0:
                pos = self.attacking_swarm.pos[i] + self.grid_offset
                gx = int(pos.x / self.grid_cell_size) + self.grid_padding
                gy = int(pos.y / self.grid_cell_size) + self.grid_padding
                gz = int(pos.z / self.grid_cell_size) + self.grid_padding
                
                gx = ti.math.clamp(gx, 0, self.grid_shape[0] - 1)
                gy = ti.math.clamp(gy, 0, self.grid_shape[1] - 1)
                gz = ti.math.clamp(gz, 0, self.grid_shape[2] - 1)
                
                idx = ti.atomic_add(self.grid_count_p[gx, gy, gz], 1)
                if idx < self.max_cell_capacity:
                    self.grid_buckets_p[gx, gy, gz, idx] = i
                    
        for i in range(self.defending_swarm.N):
            if self.defending_swarm.active[i][0] != 0:
                pos = self.defending_swarm.pos[i] + self.grid_offset
                gx = int(pos.x / self.grid_cell_size) + self.grid_padding
                gy = int(pos.y / self.grid_cell_size) + self.grid_padding
                gz = int(pos.z / self.grid_cell_size) + self.grid_padding
                
                gx = ti.math.clamp(gx, 0, self.grid_shape[0] - 1)
                gy = ti.math.clamp(gy, 0, self.grid_shape[1] - 1)
                gz = ti.math.clamp(gz, 0, self.grid_shape[2] - 1)
                
                idx = ti.atomic_add(self.grid_count_e[gx, gy, gz], 1)
                if idx < self.max_cell_capacity:
                    self.grid_buckets_e[gx, gy, gz, idx] = i

    def update_logic(self, dt: float, player_territory: float) -> None:
        self.update_shared_grid()
        self.frame_count += 1
        
        self.defending_ai.update(dt, self.attacking_swarm, player_territory)
        self.attacking_swarm.follow_path()
        
        self.attacking_swarm.update(
            dt, 
            self.grid_count_p,
            self.grid_buckets_p,
            self.grid_cell_size,
            self.grid_shape,
            self.grid_padding,
            self.grid_offset
        )
        self.defending_swarm.update(
            dt, 
            self.grid_count_e,
            self.grid_buckets_e,
            self.grid_cell_size,
            self.grid_shape,
            self.grid_padding,
            self.grid_offset
        )
        
        self.attacking_swarm.batched_combat_update(
            dt, 
            self.defending_swarm.get_pos_field(), 
            self.defending_swarm.N, 
            self.defending_swarm.health,
            self.grid_count_e,
            self.grid_buckets_e,
            self.grid_offset,
            self.grid_shape,
            self.grid_cell_size,
            self.grid_padding
        )
        
        self.defending_swarm.batched_combat_update(
            dt, 
            self.attacking_swarm.get_pos_field(), 
            self.attacking_swarm.N, 
            self.attacking_swarm.health,
            self.grid_count_p,
            self.grid_buckets_p,
            self.grid_offset,
            self.grid_shape,
            self.grid_cell_size,
            self.grid_padding
        )
        
    def update_draw(self) -> None:
        if self.frame_count % 10 == 0:
            self.attacking_swarm.update_statistics()
            self.defending_swarm.update_statistics()
        
        self.scene.particles(self.attacking_swarm.get_pos_field(), color=PLAYER_COLOR, radius=1.0)
        self.scene.particles(self.defending_swarm.get_pos_field(), color=ENEMY_COLOR, radius=1.0)
        
        self.scene.particles(self.attacking_swarm.get_projectile_pos_field(), color=PROJECTILE_COLOR, radius=0.5)
        self.scene.particles(self.defending_swarm.get_projectile_pos_field(), color=PROJECTILE_COLOR, radius=0.5)
        
        self.scene.particles(self.attacking_swarm.get_target_position(), color=TARGET_COLOR, radius=5.0)
        self.scene.particles(self.defending_swarm.get_target_position(), color=ENEMY_TARGET_COLOR, radius=5.0)
        
    def get_attacking_swarm(self) -> DroneSwarm:
        return self.attacking_swarm
    
    def get_defending_swarm(self) -> DroneSwarm:
        return self.defending_swarm
    
    def get_defending_ai(self) -> DefendingAI:
        return self.defending_ai