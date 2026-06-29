import taichi as ti
import math
from modules.constants import DroneModes
from modules.drone import DroneSwarm
from modules.gui_utils import GamePresets

class DefendingAI:
    def __init__(self, swarm: DroneSwarm, gamePreset: GamePresets) -> None:
        self.swarm = swarm
        self._update_params(gamePreset)
        
    def _update_params(self, params: GamePresets) -> None:
        self.state: DroneModes = DroneModes.ATTACK
        self.map_size = params.map_size
        self.engage_distance =  params.ai_engage_distance
        self.agression_threshold = params.ai_agression_threshold
        self.patrol_waypoints = params.ai_path_normalized
        
        self.evaluate_state_interval = params.ai_evaluate_state
        self.execute_state_interval = params.ai_execute_state
        self.evaluate_state_counter = 0
        self.execute_state_counter = 0
        
    def _get_distance_to_player(self, player_swarm: DroneSwarm) -> float:
        enemy_center = self.swarm.get_swarm_center()
        player_center = player_swarm.get_swarm_center()
        
        dx = enemy_center[0] - player_center[0]
        dy = enemy_center[1] - player_center[1]
        dz = enemy_center[2] - player_center[2]
        
        return math.sqrt(dx*dx + dy*dy + dz*dz)
    
    def _evaluate_state(self, player_swarm: DroneSwarm, player_territory: float) -> None:
        if self.evaluate_state_counter % self.evaluate_state_interval != 0:
            self.evaluate_state_counter += 1
            return
        
        distance_to_player = self._get_distance_to_player(player_swarm)
        
        new_state = self.state
        if distance_to_player <= self.engage_distance:
            new_state = DroneModes.ATTACK
        elif player_territory >= self.agression_threshold:
            new_state = DroneModes.SPREAD
        else:
            new_state = DroneModes.PATROL
        
        if self.state != new_state:
            self.state = new_state
            self.swarm.update_mode(new_state)
            
    def _execute_state(self, player_swarm: DroneSwarm) -> None:
        if self.execute_state_counter % self.execute_state_interval != 0:
            self.execute_state_counter += 1
            return

        if self.state == DroneModes.ATTACK:
            self._execute_attack(player_swarm)
        elif self.state == DroneModes.SPREAD:
            self._execute_spread(player_swarm)
        elif self.state == DroneModes.PATROL:
            self.swarm.follow_path()
            
    def _execute_attack(self, player_swarm: DroneSwarm) -> None:
        center = player_swarm.get_swarm_center()
        self.swarm.set_target(center[0], center[1], center[2])
    
    def _execute_spread(self, player_swarm: DroneSwarm) -> None:
        enemy_x, enemy_y, enemy_z = self.swarm.get_swarm_center()
        player_x, player_y, player_z = player_swarm.get_swarm_center()
        
        dx = enemy_x - player_x
        dy = enemy_y - player_y
        dz = enemy_z - player_z
        
        dist_sq = dx*dx + dy*dy + dz*dz
        
        if dist_sq > 1e-4:
            inv_dist = 1.0 / math.sqrt(dist_sq)
            retreat_distance = 100.0
            self.swarm.set_target(
                enemy_x + dx * inv_dist * retreat_distance,
                enemy_y + dy * inv_dist * retreat_distance,
                enemy_z + dz * inv_dist * retreat_distance
            )
        else:
            self.swarm.set_target(self.map_size * 0.9, self.map_size * 0.9, self.map_size * 1.0)

    def update(self, dt: float, player_swarm: DroneSwarm, player_territory: float) -> None:
        self._evaluate_state(player_swarm, player_territory)
        self._execute_state(player_swarm)