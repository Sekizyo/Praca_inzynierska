from modules.constants import GameMode
from modules.drone import DroneModes

class GuiState(str):
    def __init__(self) -> None:
        self.PAUSED: bool = False
        self.SHOW_VORONOI: bool = False
        self.SHOW_GRID: bool = False
        self.SHOW_BOUNDARY: bool = True

class EnemyAIParams(str):
    def __init__(self, map_size: float) -> None:
        self.engage_distance: float = 300.0
        self.agression_threshold: float = 0.6
        patrol_radius = map_size * 0.5
        patrol_height = map_size * 0.5
        
        self.patrol_waypoints = [
            [patrol_radius, patrol_radius, patrol_height],
            [-patrol_radius, patrol_radius, patrol_height],
            [-patrol_radius, -patrol_radius, patrol_height],
            [patrol_radius, -patrol_radius, patrol_height],
        ]
        
    def set_params(self, engage_distance: float | None, agression_threshold: float | None, patrol_waypoints: list[list[float]] | None) -> None:
        if engage_distance is not None:
            self.engage_distance = engage_distance
            
        if agression_threshold is not None:
            self.agression_threshold = agression_threshold
            
        if patrol_waypoints is not None:
            self.patrol_waypoints = patrol_waypoints

class GamePresets:
    def __init__(self) -> None:
        self.map_size: int = 250
        self.game_mode = GameMode.MISSION_PLANNING
        self.attacking_drone_count: int = 1000
        self.defending_drone_count: int = 1000
        
        #AI
        self.ai_engage_distance: int = 300
        self.ai_agression_threshold: float = 0.6
        self.ai_evaluate_state: int = 15
        self.ai_execute_state: int = 20
        self.ai_path: list[tuple[float, float, DroneModes]] = [(0.0, 0.0, DroneModes.ATTACK.value), (1.0, 1.0, DroneModes.SPREAD.value)]
        
        #Boids
        self.boids_attack_separation: float = 2.0
        self.boids_attack_alignment: float = 2.0
        self.boids_attack_cohesion: float = 1.5
        self.boids_attack_target: float = 2.0
        
        self.boids_spread_separation: float = 3.5
        self.boids_spread_alignment: float = 0.7
        self.boids_spread_cohesion: float = 0.3
        self.boids_spread_target: float = 1.0
        
        #Drone
        self.attacking_path: list[tuple[float, float, DroneModes]] = [(0.0, 0.0, DroneModes.ATTACK.value), (1.0, 1.0, DroneModes.SPREAD.value)]
        self.drone_mode: DroneModes = DroneModes.ATTACK
        self.drone_max_speed: int = 20
        self.drone_perception_radius: int = 40
        self.drone_shooting_range: int = 50
        self.drone_shooting_cooldown: int = 2
        self.drone_hit_radius: int = 2
        self.drone_max_health: int = 100
        
        # Projectile
        self.projectile_speed: int = 50
        self.projectile_damage: int = 25
        self.projectile_max_lifetime: int = 1
        self.projectile_radius: int = 1
        
    def compare(self, other: "GamePresets") -> bool:
        if self.attacking_drone_count != other.attacking_drone_count:
            return False
        if self.defending_drone_count != other.defending_drone_count:
            return False
        return True
    
    def generate_config_dict(self) -> dict[str, tuple[float | int | list[tuple[float, float, DroneModes]], str]]:
        return {
            "map_size": (self.map_size, f"Type: int, Range: (50, 1000), Default: {self.map_size}"),
            "attacking_drone_count": (self.attacking_drone_count, f"Type: int, Range: (1, 8000), Default: {self.attacking_drone_count}"),
            "defending_drone_count": (self.defending_drone_count, f"Type: int, Range: (1, 8000), Default: {self.defending_drone_count}"),
            
            "ai_path": (self.ai_path, f"Type: list[tuple[float, float, 'attack' | 'spread']], Range: (-1, 1), Default: {self.ai_path}"),
            "ai_engage_distance": (self.ai_engage_distance, f"Type: int, Range: (0, map_size), Default: {self.ai_engage_distance}"),
            "ai_agression_threshold": (self.ai_agression_threshold, f"Type: float, Range: (0, 1), Default: {round(self.ai_agression_threshold, 2)}"),
            "ai_evaluate_state": (self.ai_evaluate_state, f"Type: int, Range: (1, 50), Default: {self.ai_evaluate_state}"),
            "ai_execute_state": (self.ai_execute_state, f"Type: int, Range: (1, 50), Default: {self.ai_execute_state}"),
            
            "boids_attack_cohesion": (self.boids_attack_cohesion, f"Type: int, Range: (1, 10), Default: {self.boids_attack_cohesion}"),
            "boids_attack_separation": (self.boids_attack_separation, f"Type: int, Range: (1, 10), Default: {self.boids_attack_separation}"),
            "boids_attack_alignment": (self.boids_attack_alignment, f"Type: int, Range: (1, 10), Default: {self.boids_attack_alignment}"),
            "boids_attack_target": (self.boids_attack_target, f"Type: int, Range: (1, 10), Default: {self.boids_attack_target}"),
            "boids_spread_cohesion": (self.boids_spread_cohesion, f"Type: int, Range: (1, 10), Default: {self.boids_spread_cohesion}"),
            "boids_spread_separation": (self.boids_spread_separation, f"Type: int, Range: (1, 10), Default: {self.boids_spread_separation}"),
            "boids_spread_alignment": (self.boids_spread_alignment, f"Type: int, Range: (1, 10), Default: {self.boids_spread_alignment}"),
            "boids_spread_target": (self.boids_spread_target, f"Type: int, Range: (1, 10), Default: {self.boids_spread_target}"),
            
            "drone_path": (self.attacking_path, f"Type: list[tuple[float, float, 'attack' | 'spread']], Range: (-1, 1), Default: {self.attacking_path}"),
            "drone_max_speed": (self.drone_max_speed, f"Type: int, Range: (1, 100), Default: {self.drone_max_speed}"),
            "drone_shooting_range": (self.drone_shooting_range, f"Type: int, Range: (0, map_size), Default: {self.drone_shooting_range}"),
            "drone_shooting_cooldown": (self.drone_shooting_cooldown, f"Type: int, Range: (0, 100), Default: {self.drone_shooting_cooldown}"),
            "drone_max_health": (self.drone_max_health, f"Type: int, Range: (1, 100), Default: {self.drone_max_health}"),
            "drone_perception_radius": (self.drone_perception_radius, f"Type: int, Range: (0, 360), Default: {self.drone_perception_radius}"),
            "drone_hit_radius": (self.drone_hit_radius, f"Type: int, Range: (1, 5), Default: {self.drone_hit_radius}"),
            
            "projectile_damage": (self.projectile_damage, f"Type: int, Range: (1, drone_max_health), Default: {self.projectile_damage}"),
            "projectile_radius": (self.projectile_radius, f"Type: int, Range: (1, 5), Default: {self.projectile_radius}"),
            "projectile_max_lifetime": (self.projectile_max_lifetime, f"Type: float, Range: (0.5, 10), Default: {self.projectile_max_lifetime}")
        }
        
        
    def load_config(self, config: dict[str, tuple[float | int | list[tuple[float, float, DroneModes]]]] | None) -> None:
        if not config:
            return
        
        self.map_size = config.get("map_size", self.map_size)
        self.attacking_drone_count = config.get("attacking_drone_count", self.attacking_drone_count)
        self.defending_drone_count = config.get("defending_drone_count", self.defending_drone_count)
        
        self.ai_path = config.get("ai_path", self.ai_path)
        self.ai_engage_distance = config.get("ai_engage_distance", self.ai_engage_distance)
        self.ai_agression_threshold = round(config.get("ai_agression_threshold", self.ai_agression_threshold), 2)
        self.ai_evaluate_state = config.get("ai_evaluate_state", self.ai_evaluate_state)
        self.ai_execute_state = config.get("ai_execute_state", self.ai_execute_state)
        
        
        self.boids_attack_separation = config.get("boids_attack_separation", self.boids_attack_separation)
        self.boids_attack_alignment = config.get("boids_attack_alignment", self.boids_attack_alignment)
        self.boids_attack_cohesion = config.get("boids_attack_cohesion", self.boids_attack_cohesion)
        self.boids_attack_target = config.get("boids_attack_target", self.boids_attack_target)

        self.boids_spread_separation = config.get("boids_spread_separation", self.boids_spread_separation)  
        self.boids_spread_alignment = config.get("boids_spread_alignment", self.boids_spread_alignment)
        self.boids_spread_cohesion = config.get("boids_spread_cohesion", self.boids_spread_cohesion)
        self.boids_spread_target = config.get("boids_spread_target", self.boids_spread_target)

        self.attacking_path = config.get("drone_path", self.attacking_path)
        self.drone_max_speed = config.get("drone_max_speed", self.drone_max_speed)
        self.drone_shooting_range = config.get("drone_shooting_range", self.drone_shooting_range)
        self.drone_shooting_cooldown = config.get("drone_shooting_cooldown", self.drone_shooting_cooldown)
        self.drone_max_health = config.get("drone_max_health", self.drone_max_health)
        self.drone_perception_radius = config.get("drone_perception_radius", self.drone_perception_radius)
        self.drone_hit_radius = config.get("drone_hit_radius", self.drone_hit_radius)
        
        self.projectile_damage = config.get("projectile_damage", self.projectile_damage)
        self.projectile_radius = config.get("projectile_radius", self.projectile_radius)
        self.projectile_max_lifetime = config.get("projectile_max_lifetime", self.projectile_max_lifetime)