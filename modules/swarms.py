from modules.drone import DroneSwarm
from modules.colors import PLAYER_COLOR, ENEMY_COLOR, PROJECTILE_COLOR
import taichi as ti
from taichi.ui.scene import SceneV2

from modules.colors import TARGET_COLOR
from modules.gui_utils import GuiState

class Swarms():
    def __init__(self, scene: SceneV2, drone_count: int, map_size: float) -> None:
        self.scene = scene
        self.map_size = map_size
        self.drone_count = drone_count
        self.player_swarm = DroneSwarm(count=drone_count, boundary_size=map_size, team=0)
        self.enemy_swarm = DroneSwarm(count=drone_count, boundary_size=map_size, team=1)
        self._init_swarms()
        
    def _init_swarms(self) -> None:
        self.player_target_field = ti.Vector.field(3, dtype=ti.f32, shape=1)
        self.player_target_field[0] = [-self.map_size, 0.0, 0.0]
        
        self.enemy_target_field = ti.Vector.field(3, dtype=ti.f32, shape=1)
        self.enemy_target_field[0] = [100.0, 0.0, 0.0]
        
    def _update_logic(self, dt: float) -> None:
        self.player_swarm.update(dt=dt, target_pos=self.player_target_field)
        self.enemy_swarm.update(dt=dt, target_pos=self.enemy_target_field)
        
        self.player_swarm.shoot(self.enemy_swarm.get_pos_field(), self.enemy_swarm.N, self.enemy_swarm.health)
        self.enemy_swarm.shoot(self.player_swarm.get_pos_field(), self.player_swarm.N, self.player_swarm.health)
        
        self.player_swarm.update_projectiles(dt=dt)
        self.enemy_swarm.update_projectiles(dt=dt)
        
        self.player_swarm.check_hits(self.enemy_swarm.get_pos_field(), self.enemy_swarm.N, self.enemy_swarm.health)
        self.enemy_swarm.check_hits(self.player_swarm.get_pos_field(), self.player_swarm.N, self.player_swarm.health)
        
        self.player_swarm.update_health()
        self.enemy_swarm.update_health()
        
    def _draw(self, gui_state: GuiState) -> None:
        if gui_state.SHOW_SHOOT_RANGE:
            self.player_swarm.compute_range_circles()
            self.enemy_swarm.compute_range_circles()
        
            self.scene.lines(self.player_swarm.get_range_circles(), color=PLAYER_COLOR, width=2.0)
            self.scene.lines(self.enemy_swarm.get_range_circles(), color=ENEMY_COLOR, width=2.0)
            
        self.scene.particles(self.player_swarm.get_pos_field(), color=PLAYER_COLOR, radius=1.0)
        self.scene.particles(self.enemy_swarm.get_pos_field(), color=ENEMY_COLOR, radius=1.0)
        
        self.scene.particles(self.player_swarm.get_projectile_pos_field(), color=PROJECTILE_COLOR, radius=0.5)
        self.scene.particles(self.enemy_swarm.get_projectile_pos_field(), color=PROJECTILE_COLOR, radius=0.5)
        
        self.scene.particles(self.get_player_target(), color=TARGET_COLOR, radius=1.0)
        
    def get_player_swarm(self) -> DroneSwarm:
        return self.player_swarm
    
    def get_enemy_swarm(self) -> DroneSwarm:
        return self.enemy_swarm
    
    def get_player_target(self):
        return self.player_target_field
    
    def set_player_target(self, x: float, y: float) -> None:
        self.player_target_field[0] = [x, y, 250]
        
    def update(self, dt: float, gui_state: GuiState) -> None:
        self._update_logic(dt)
        self._draw(gui_state)