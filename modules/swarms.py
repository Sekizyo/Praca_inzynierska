from modules.drone import DroneSwarm
from modules.colors import PLAYER_COLOR, ENEMY_COLOR, PROJECTILE_COLOR, GRID_COLOR
import taichi as ti
from taichi.ui.scene import SceneV2

from modules.colors import TARGET_COLOR, ENEMY_TARGET_COLOR
from modules.gui_utils import GuiState
from modules.enemy_ai import EnemyAI

@ti.data_oriented
class Swarms():
    def __init__(self, scene: SceneV2, drone_count: int, map_size: float) -> None:
        self.scene = scene
        self.map_size = map_size
        self.drone_count = drone_count
        self.player_swarm = DroneSwarm(count=drone_count, boundary_size=map_size, team=0)
        self.enemy_swarm = DroneSwarm(count=drone_count, boundary_size=map_size, team=1)
        self.enemy_ai = EnemyAI(self.enemy_swarm, map_size)
        self._init_swarms()
        
    def _init_swarms(self) -> None:
        self.player_target_field = ti.Vector.field(3, dtype=ti.f32, shape=1)
        self.player_target_field[0] = [-self.map_size, 0.0, 0.0]
        
        self.grid_cell_size = 40.0
        self.grid_padding = 2
        self.max_cell_capacity = 300
        
        grid_dim = int(self.map_size * 2 / self.grid_cell_size) + 2 * self.grid_padding
        self.grid_shape = ti.Vector([grid_dim, grid_dim, grid_dim])
        self.grid_offset = ti.Vector([self.map_size, self.map_size, 0.0])
        
        self.grid_count_p = ti.field(dtype=ti.i32, shape=self.grid_shape)
        self.grid_buckets_p = ti.field(dtype=ti.i32, shape=(self.grid_shape[0], self.grid_shape[1], self.grid_shape[2], self.max_cell_capacity))
        self.grid_count_e = ti.field(dtype=ti.i32, shape=self.grid_shape)
        self.grid_buckets_e = ti.field(dtype=ti.i32, shape=(self.grid_shape[0], self.grid_shape[1], self.grid_shape[2], self.max_cell_capacity))
        
        self.max_grid_lines = 60000
        self.grid_lines = ti.Vector.field(3, dtype=ti.f32, shape=self.max_grid_lines * 2)
        self.grid_line_count = ti.field(dtype=ti.i32, shape=())

    @ti.kernel
    def update_shared_grid(self):
        for I in ti.grouped(self.grid_count_p):
            self.grid_count_p[I] = 0
            self.grid_count_e[I] = 0
            
        for i in range(self.player_swarm.N):
            if self.player_swarm.active[i][0] != 0:
                pos = self.player_swarm.pos[i] + self.grid_offset
                gx = int(pos.x / self.grid_cell_size) + self.grid_padding
                gy = int(pos.y / self.grid_cell_size) + self.grid_padding
                gz = int(pos.z / self.grid_cell_size) + self.grid_padding
                
                gx = ti.math.clamp(gx, 0, self.grid_shape[0] - 1)
                gy = ti.math.clamp(gy, 0, self.grid_shape[1] - 1)
                gz = ti.math.clamp(gz, 0, self.grid_shape[2] - 1)
                
                idx = ti.atomic_add(self.grid_count_p[gx, gy, gz], 1)
                if idx < self.max_cell_capacity:
                    self.grid_buckets_p[gx, gy, gz, idx] = i
                    
        for i in range(self.enemy_swarm.N):
            if self.enemy_swarm.active[i][0] != 0:
                pos = self.enemy_swarm.pos[i] + self.grid_offset
                gx = int(pos.x / self.grid_cell_size) + self.grid_padding
                gy = int(pos.y / self.grid_cell_size) + self.grid_padding
                gz = int(pos.z / self.grid_cell_size) + self.grid_padding
                
                gx = ti.math.clamp(gx, 0, self.grid_shape[0] - 1)
                gy = ti.math.clamp(gy, 0, self.grid_shape[1] - 1)
                gz = ti.math.clamp(gz, 0, self.grid_shape[2] - 1)
                
                idx = ti.atomic_add(self.grid_count_e[gx, gy, gz], 1)
                if idx < self.max_cell_capacity:
                    self.grid_buckets_e[gx, gy, gz, idx] = i

    @ti.kernel
    def update_grid_vis(self):
        self.grid_line_count[None] = 0
        
        for I in ti.grouped(self.grid_count_p):
            if self.grid_count_p[I] > 0 or self.grid_count_e[I] > 0:
                base_x = (I[0] - self.grid_padding) * self.grid_cell_size - self.grid_offset.x
                base_y = (I[1] - self.grid_padding) * self.grid_cell_size - self.grid_offset.y
                base_z = (I[2] - self.grid_padding) * self.grid_cell_size - self.grid_offset.z
                
                size = self.grid_cell_size
                
                idx = ti.atomic_add(self.grid_line_count[None], 24)
                
                if idx + 24 <= self.max_grid_lines * 2:
                    p0 = ti.Vector([base_x, base_y, base_z])
                    p1 = ti.Vector([base_x + size, base_y, base_z])
                    p2 = ti.Vector([base_x + size, base_y + size, base_z])
                    p3 = ti.Vector([base_x, base_y + size, base_z])
                    
                    p4 = ti.Vector([base_x, base_y, base_z + size])
                    p5 = ti.Vector([base_x + size, base_y, base_z + size])
                    p6 = ti.Vector([base_x + size, base_y + size, base_z + size])
                    p7 = ti.Vector([base_x, base_y + size, base_z + size])
                    
                    # Bottom
                    self.grid_lines[idx] = p0; self.grid_lines[idx+1] = p1
                    self.grid_lines[idx+2] = p1; self.grid_lines[idx+3] = p2
                    self.grid_lines[idx+4] = p2; self.grid_lines[idx+5] = p3
                    self.grid_lines[idx+6] = p3; self.grid_lines[idx+7] = p0
                    
                    # Top
                    self.grid_lines[idx+8] = p4; self.grid_lines[idx+9] = p5
                    self.grid_lines[idx+10] = p5; self.grid_lines[idx+11] = p6
                    self.grid_lines[idx+12] = p6; self.grid_lines[idx+13] = p7
                    self.grid_lines[idx+14] = p7; self.grid_lines[idx+15] = p4
                    
                    # Vertical
                    self.grid_lines[idx+16] = p0; self.grid_lines[idx+17] = p4
                    self.grid_lines[idx+18] = p1; self.grid_lines[idx+19] = p5
                    self.grid_lines[idx+20] = p2; self.grid_lines[idx+21] = p6
                    self.grid_lines[idx+22] = p3; self.grid_lines[idx+23] = p7

    def _update_logic(self, dt: float, player_territory: float) -> None:
        self.update_shared_grid()
        
        # Update statistics once per frame (batched kernel)
        self.player_swarm.update_statistics()
        self.enemy_swarm.update_statistics()

        self.enemy_ai.update(dt, self.player_swarm, player_territory)
        
        self.player_swarm.update(
            dt, 
            self.player_target_field,
            self.grid_count_p,
            self.grid_buckets_p,
            self.grid_cell_size,
            self.grid_shape,
            self.grid_padding,
            self.grid_offset
        )
        self.enemy_swarm.update(
            dt, 
            self.enemy_ai.get_target_field(),
            self.grid_count_e,
            self.grid_buckets_e,
            self.grid_cell_size,
            self.grid_shape,
            self.grid_padding,
            self.grid_offset
        )
        
        self.player_swarm.batched_combat_update(
            dt, 
            self.enemy_swarm.get_pos_field(), 
            self.enemy_swarm.N, 
            self.enemy_swarm.health,
            self.grid_count_e,
            self.grid_buckets_e,
            self.grid_offset,
            self.grid_shape,
            self.grid_cell_size,
            self.grid_padding
        )
        
        self.enemy_swarm.batched_combat_update(
            dt, 
            self.player_swarm.get_pos_field(), 
            self.player_swarm.N, 
            self.player_swarm.health,
            self.grid_count_p,
            self.grid_buckets_p,
            self.grid_offset,
            self.grid_shape,
            self.grid_cell_size,
            self.grid_padding
        )
        
    def _draw(self, gui_state: GuiState) -> None:
        if gui_state.SHOW_GRID:
            self.update_grid_vis()
            self.scene.lines(self.grid_lines, color=GRID_COLOR, width=1.0)

        self.scene.particles(self.player_swarm.get_pos_field(), color=PLAYER_COLOR, radius=1.0)
        self.scene.particles(self.enemy_swarm.get_pos_field(), color=ENEMY_COLOR, radius=1.0)
        
        self.scene.particles(self.player_swarm.get_projectile_pos_field(), color=PROJECTILE_COLOR, radius=0.5)
        self.scene.particles(self.enemy_swarm.get_projectile_pos_field(), color=PROJECTILE_COLOR, radius=0.5)
        
        self.scene.particles(self.get_player_target(), color=TARGET_COLOR, radius=5.0)
        self.scene.particles(self.enemy_ai.get_target_field(), color=ENEMY_TARGET_COLOR, radius=5.0)
        
    def get_player_swarm(self) -> DroneSwarm:
        return self.player_swarm
    
    def get_enemy_swarm(self) -> DroneSwarm:
        return self.enemy_swarm
    
    def get_enemy_ai(self) -> EnemyAI:
        return self.enemy_ai
    
    def get_player_target(self):
        return self.player_target_field
    
    def set_player_target(self, x: float, y: float) -> None:
        self.player_target_field[0] = [x, y, self.map_size * 0.5]
        
    def update_logic(self, dt: float, player_territory: float) -> None:
        self._update_logic(dt, player_territory)
        
    def update_draw(self, gui_state: GuiState) -> None:
        self._draw(gui_state)