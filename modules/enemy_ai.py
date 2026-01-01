import taichi as ti
import math
from modules.constants import DroneModes
from modules.drone import DroneSwarm


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
        self.decision_interval = 60.0  # Make decisions every N seconds
        
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
        
        # Cache for center calculations
        self._swarm_center_cache = [0.0, 0.0, 0.0]
        self._player_center_cache = [0.0, 0.0, 0.0]
        self._cache_valid = False
    
    def get_target_field(self):
        """Return the target field for the enemy swarm"""
        return self.target_field
    
    def update(self, dt: float, player_swarm: DroneSwarm) -> None:
        """Update AI state machine and behavior"""
        self.state_timer += dt
        self.decision_cooldown -= dt
        
        # Invalidate cache each frame
        self._cache_valid = False
        
        # Make tactical decisions at intervals
        if self.decision_cooldown <= 0:
            self._evaluate_state(player_swarm)
            self.decision_cooldown = self.decision_interval
        
        # Execute current state behavior
        self._execute_state(dt, player_swarm)
    
    def _evaluate_state(self, player_swarm: DroneSwarm) -> None:
        """Evaluate conditions and potentially transition to new state"""
        # Calculate metrics (cached)
        enemy_health_ratio = self._get_swarm_health_ratio()
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
    
    def _execute_state(self, dt: float, player_swarm: DroneSwarm) -> None:
        """Execute behavior for current state"""
        if self.state == DroneModes.PATROL:
            self._execute_patrol()
        elif self.state == DroneModes.ATTACK:
            self._execute_attack(player_swarm)
        else:  # SPREAD
            self._execute_spread(player_swarm)
    
    def _execute_patrol(self) -> None:
        """Patrol between waypoints"""
        current_target = self.patrol_waypoints[self.current_waypoint]
        self.target_field[0] = current_target
        
        # Check if reached waypoint (using cached center)
        swarm_center = self._get_swarm_center()
        dx = swarm_center[0] - current_target[0]
        dy = swarm_center[1] - current_target[1]
        dz = swarm_center[2] - current_target[2]
        
        if (dx*dx + dy*dy + dz*dz) < 2500.0:  # 50^2
            self.current_waypoint = (self.current_waypoint + 1) % len(self.patrol_waypoints)
    
    def _execute_attack(self, player_swarm: DroneSwarm) -> None:
        """Attack - move directly to player"""
        self.target_field[0] = self._get_player_center(player_swarm)
    
    def _execute_spread(self, player_swarm: DroneSwarm) -> None:
        """Defensive spread - move away from player"""
        player_center = self._get_player_center(player_swarm)
        swarm_center = self._get_swarm_center()
        
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
    
    def _get_swarm_center(self) -> list[float]:
        """Calculate the center of the enemy swarm with caching"""
        if self._cache_valid:
            return self._swarm_center_cache
        
        total_x = total_y = total_z = 0.0
        count = 0
        
        for i in range(self.swarm.N):
            if self.swarm.active[i] == 1:
                total_x += self.swarm.pos[i][0]
                total_y += self.swarm.pos[i][1]
                total_z += self.swarm.pos[i][2]
                count += 1
        
        if count > 0:
            inv_count = 1.0 / count
            self._swarm_center_cache[0] = total_x * inv_count
            self._swarm_center_cache[1] = total_y * inv_count
            self._swarm_center_cache[2] = total_z * inv_count
        else:
            self._swarm_center_cache[:] = [0.0, 0.0, 0.0]
        
        return self._swarm_center_cache
    
    def _get_player_center(self, player_swarm: DroneSwarm) -> list[float]:
        """Calculate the center of the player swarm with caching"""
        if self._cache_valid:
            return self._player_center_cache
        
        total_x = total_y = total_z = 0.0
        count = 0
        
        for i in range(player_swarm.N):
            if player_swarm.active[i] == 1:
                total_x += player_swarm.pos[i][0]
                total_y += player_swarm.pos[i][1]
                total_z += player_swarm.pos[i][2]
                count += 1
        
        if count > 0:
            inv_count = 1.0 / count
            self._player_center_cache[0] = total_x * inv_count
            self._player_center_cache[1] = total_y * inv_count
            self._player_center_cache[2] = total_z * inv_count
        else:
            self._player_center_cache[:] = [0.0, 0.0, 0.0]
        
        self._cache_valid = True
        return self._player_center_cache
    
    def _get_distance_to_player(self, player_swarm: DroneSwarm) -> float:
        """Calculate distance between swarm centers (optimized)"""
        swarm_center = self._get_swarm_center()
        player_center = self._get_player_center(player_swarm)
        
        dx = swarm_center[0] - player_center[0]
        dy = swarm_center[1] - player_center[1]
        dz = swarm_center[2] - player_center[2]
        
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    
    def _get_swarm_health_ratio(self) -> float:
        """Get average health ratio of enemy swarm (optimized)"""
        total_health = 0.0
        count = 0
        
        for i in range(self.swarm.N):
            if self.swarm.active[i] == 1:
                total_health += self.swarm.health[i]
                count += 1
        
        return (total_health / count / self.swarm.max_health) if count > 0 else 0.0
    
    def get_state(self) -> DroneModes:
        """Get current AI state"""
        return self.state
