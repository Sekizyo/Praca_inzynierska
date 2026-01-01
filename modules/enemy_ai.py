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
        self.engage_distance = 200.0  # Distance to start attacking player
        self.health_spread_threshold = 0.4  # Health ratio to trigger spread
        
        # State timers
        self.state_timer = 0.0
        self.decision_cooldown = 0.0
        self.decision_interval = 15.0  # Make decisions every N seconds
        
        # Patrol waypoints
        half_size = map_size * 0.5
        self.patrol_waypoints = [
            [map_size * 0.8, map_size * 0.8, half_size],
            [map_size * 0.8, -map_size * 0.8, half_size],
            [half_size, 0.0, map_size * 0.7],
        ]
        self.current_waypoint = 0
        
        # Target field
        self.target_field = ti.Vector.field(3, dtype=ti.f32, shape=1)
        self.target_field[0] = self.patrol_waypoints[0]
    
    def get_target_field(self):
        return self.target_field
    
    @run_every_n_calls(10)
    def update(self, dt: float, player_swarm: DroneSwarm) -> None:
        self._evaluate_state(player_swarm)
        self._execute_state(player_swarm)
        
    @run_every_n_calls(10)
    def _evaluate_state(self, player_swarm: DroneSwarm) -> None:
        # Calculate metrics (cached)
        enemy_health_ratio = self.swarm.get_health_ratio()
        distance_to_player = self._get_distance_to_player(player_swarm)
        
        # Determine new state
        if enemy_health_ratio < self.health_spread_threshold:
            new_state = DroneModes.SPREAD
        elif distance_to_player < self.engage_distance and enemy_health_ratio > 0.5:
            new_state = DroneModes.ATTACK
        else:
            new_state = DroneModes.PATROL
        
        # Update state if changed
        if self.state != new_state:
            self.state = new_state
            self.state_timer = 0.0
            self.swarm.update_mode(DroneModes[new_state.value.upper()])
    
    @run_every_n_calls(10)
    def _execute_state(self, player_swarm: DroneSwarm) -> None:
        if self.state == DroneModes.PATROL:
            self._execute_patrol()
        elif self.state == DroneModes.ATTACK:
            self._execute_attack(player_swarm)
        elif self.state == DroneModes.SPREAD:
            self._execute_spread(player_swarm)
    
    def _execute_patrol(self) -> None:
        """Patrol between waypoints"""
        current_target = self.patrol_waypoints[self.current_waypoint]
        self.target_field[0] = current_target
        
        # Check if reached waypoint (using cached center)
        swarm_center = self.swarm.get_swarm_center()
        dx = swarm_center[0] - current_target[0]
        dy = swarm_center[1] - current_target[1]
        dz = swarm_center[2] - current_target[2]
        
        if (dx*dx + dy*dy + dz*dz) < 2500.0:  # 50^2
            self.current_waypoint = (self.current_waypoint + 1) % len(self.patrol_waypoints)
    
    def _execute_attack(self, player_swarm: DroneSwarm) -> None:
        """Attack - move directly to player"""
        self.target_field[0] = player_swarm.get_swarm_center()
    
    def _execute_spread(self, player_swarm: DroneSwarm) -> None:
        """Defensive spread - move away from player"""
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
            self.target_field[0] = [self.map_size * 0.8, self.map_size * 0.8, self.map_size * 0.5]
    
    def _get_distance_to_player(self, player_swarm: DroneSwarm) -> float:
        swarm_center = self.swarm.get_swarm_center()
        player_center = player_swarm.get_swarm_center()
        
        dx = swarm_center[0] - player_center[0]
        dy = swarm_center[1] - player_center[1]
        dz = swarm_center[2] - player_center[2]
        
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    
    def get_state(self) -> DroneModes:
        return self.state
