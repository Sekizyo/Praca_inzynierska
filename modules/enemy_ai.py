import taichi as ti
import math
from modules.constants import DroneModes
from modules.drone import DroneSwarm
from modules.utils import run_every_n_calls

class EnemyAI:
    def __init__(self, enemy_swarm: DroneSwarm, map_size: float):
        self.swarm = enemy_swarm
        self.map_size = map_size
        self.state = DroneModes.PATROL
        
        # AI parameters
        self.engage_distance = 400.0
        self.health_spread_threshold = 0.7
        
        # Patrol waypoints
        half_size = map_size * 0.5
        self.patrol_waypoints = [
            [half_size, half_size, half_size],
        ]
        self.current_waypoint = 0
        
        # Target field
        self.target_field = ti.Vector.field(3, dtype=ti.f32, shape=1)
        self.target_field[0] = self.patrol_waypoints[0]
    
    def get_target_field(self):
        return self.target_field
    
    def _get_distance_to_player(self, player_swarm: DroneSwarm) -> float:
        swarm_center = self.swarm.get_swarm_center()
        player_center = player_swarm.get_swarm_center()
        
        dx = swarm_center[0] - player_center[0]
        dy = swarm_center[1] - player_center[1]
        dz = swarm_center[2] - player_center[2]
        
        return math.sqrt(dx * dx + dy * dy + dz * dz)
    
    def update(self, dt: float, player_swarm: DroneSwarm, player_territory: float) -> None:
        self._evaluate_state(player_swarm, player_territory)
        self._execute_state(player_swarm)
        
    def _evaluate_state(self, player_swarm: DroneSwarm, player_territory: float) -> None:
        health_ratio = self.swarm.get_health_ratio()
        distance_to_player = self._get_distance_to_player(player_swarm)
        
        agression: float = round(player_territory / 100, 2)
        print(agression)
        if health_ratio < self.health_spread_threshold or agression < 0.5:
            new_state = DroneModes.SPREAD
        elif distance_to_player < self.engage_distance and health_ratio > 0.5 or agression >= 0.5:
            new_state = DroneModes.ATTACK
        else:
            new_state = DroneModes.PATROL
        
        if self.state != new_state:
            self.state = new_state
            self.swarm.update_mode(new_state)
            
    @run_every_n_calls(10)
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
    
    def _execute_attack(self, player_swarm: DroneSwarm) -> None:
        self.target_field[0] = player_swarm.get_swarm_center()
        self.target_field[0][2] = self.map_size * 0.5 
    
    def _execute_spread(self, player_swarm: DroneSwarm) -> None:
        player_center = player_swarm.get_swarm_center()
        swarm_center = self.swarm.get_swarm_center()
        
        dx = swarm_center[0] - player_center[0]
        dy = swarm_center[1] - player_center[1]
        dz = swarm_center[2] - player_center[2]
        dist_sq = dx*dx + dy*dy + dz*dz
        
        if dist_sq > 0.01:
            inv_dist = 1.0 / math.sqrt(dist_sq)
            self.target_field[0] = [
                swarm_center[0] + dx * inv_dist * 100.0,
                swarm_center[1] + dy * inv_dist * 100.0,
                swarm_center[2]
            ]
        else:
            self.target_field[0] = [self.map_size * 0.9, self.map_size * 0.9, self.map_size * 1.0]
    
    def get_state(self) -> DroneModes:
        return self.state
