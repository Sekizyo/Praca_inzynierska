from turtle import distance
import taichi as ti
import math
from modules.constants import DroneModes
from modules.drone import DroneSwarm
from modules.utils import run_every_n_calls

@ti.data_oriented
class EnemyAI:
    def __init__(self, enemy_swarm: DroneSwarm, map_size: float):
        self.swarm = enemy_swarm
        self.map_size = map_size
        self.state = DroneModes.PATROL
        
        self.engage_distance = 300.0
        
        patrol_radius = map_size * 0.5
        patrol_height = map_size * 0.5
        
        self.patrol_waypoints = [
            [patrol_radius, patrol_radius, patrol_height],
            [-patrol_radius, patrol_radius, patrol_height],
            [-patrol_radius, -patrol_radius, patrol_height],
            [patrol_radius, -patrol_radius, patrol_height],
        ]
        self.current_waypoint = 0
        
        self.target_field = ti.Vector.field(3, dtype=ti.f32, shape=1)
        self.target_field[0] = self.patrol_waypoints[0]
    
    def get_target_field(self):
        return self.target_field
    
    def _get_distance_to_player(self, player_swarm: DroneSwarm) -> float:
        enemy_center = self.swarm.get_swarm_center()
        player_center = player_swarm.get_swarm_center()
        
        dx = enemy_center[0] - player_center[0]
        dy = enemy_center[1] - player_center[1]
        dz = enemy_center[2] - player_center[2]
        
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    
    def update(self, dt: float, player_swarm: DroneSwarm, player_territory: float) -> None:
        self._evaluate_state(player_swarm, player_territory)
        self._execute_state(player_swarm)
        
    @run_every_n_calls(15)
    def _evaluate_state(self, player_swarm: DroneSwarm, player_territory: float) -> None:
        distance_to_player = self._get_distance_to_player(player_swarm)
        
        agression: float = round(player_territory / 100, 2)
        if distance_to_player > self.engage_distance:
            new_state = DroneModes.PATROL
        elif agression < 0.6:
            new_state = DroneModes.SPREAD
        elif distance_to_player < self.engage_distance or agression >= 0.6:
            new_state = DroneModes.ATTACK
        
        if self.state != new_state:
            self.state = new_state
            self.swarm.update_mode(new_state)
            
    @run_every_n_calls(20)
    def _execute_state(self, player_swarm: DroneSwarm) -> None:
        if self.state == DroneModes.PATROL:
            self._execute_patrol()
        elif self.state == DroneModes.ATTACK:
            self._execute_attack(player_swarm)
        elif self.state == DroneModes.SPREAD:
            self._execute_spread(player_swarm)
    
    def _execute_patrol(self) -> None:
        current_target = self.patrol_waypoints[self.current_waypoint]
        self.target_field[0] = current_target
        
        swarm_center = self.swarm.get_swarm_center()
        dist = math.sqrt(
            (swarm_center[0] - current_target[0])**2 +
            (swarm_center[1] - current_target[1])**2 +
            (swarm_center[2] - current_target[2])**2
        )
        
        if dist < 50.0:
            self.current_waypoint = (self.current_waypoint + 1) % len(self.patrol_waypoints)
    
    def _execute_attack(self, player_swarm: DroneSwarm) -> None:
        self.target_field[0] = player_swarm.get_swarm_center()
        self.target_field[0][2] = self.map_size * 0.5 
    
    @ti.kernel
    def _compute_retreat_direction(self, player_pos: ti.template(), player_count: ti.i32, player_health: ti.template()):
        enemy_x = 0.0
        enemy_y = 0.0
        enemy_z = 0.0
        enemy_count = 0
        
        for i in range(self.swarm.N):
            if self.swarm.active[i] == 1:
                enemy_x += self.swarm.pos[i].x
                enemy_y += self.swarm.pos[i].y
                enemy_z += self.swarm.pos[i].z
                enemy_count += 1
        
        player_x = 0.0
        player_y = 0.0
        player_z = 0.0
        p_count = 0
        
        for i in range(player_count):
            if player_health[i] > 0.0:
                player_x += player_pos[i].x
                player_y += player_pos[i].y
                player_z += player_pos[i].z
                p_count += 1
        
        if enemy_count > 0 and p_count > 0:
            enemy_x /= ti.cast(enemy_count, ti.f32)
            enemy_y /= ti.cast(enemy_count, ti.f32)
            enemy_z /= ti.cast(enemy_count, ti.f32)
            
            player_x /= ti.cast(p_count, ti.f32)
            player_y /= ti.cast(p_count, ti.f32)
            player_z /= ti.cast(p_count, ti.f32)
            
            dx = enemy_x - player_x
            dy = enemy_y - player_y
            dz = enemy_z - player_z
            dist_sq = dx*dx + dy*dy + dz*dz
            
            if dist_sq > 1e-4:
                inv_dist = ti.rsqrt(dist_sq)
                retreat_distance = 100.0
                self.target_field[0] = ti.Vector([
                    enemy_x + dx * inv_dist * retreat_distance,
                    enemy_y + dy * inv_dist * retreat_distance,
                    enemy_z
                ])
            else:
                self.target_field[0] = ti.Vector([self.map_size * 0.9, self.map_size * 0.9, self.map_size * 1.0])
        else:
            self.target_field[0] = ti.Vector([self.map_size * 0.9, self.map_size * 0.9, self.map_size * 1.0])
    
    def _execute_spread(self, player_swarm: DroneSwarm) -> None:
        self._compute_retreat_direction(player_swarm.pos, player_swarm.N, player_swarm.health)
    
    def get_state(self) -> DroneModes:
        return self.state
