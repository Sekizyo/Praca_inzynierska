from modules.constants import GameMode
from typing import Union, Optional
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
        
    def set_params(self, engage_distance: Optional[float], agression_threshold: Optional[float], patrol_waypoints: Optional[list[list[float]]]) -> None:
        if engage_distance is not None:
            self.engage_distance = engage_distance
            
        if agression_threshold is not None:
            self.agression_threshold = agression_threshold
            
        if patrol_waypoints is not None:
            self.patrol_waypoints = patrol_waypoints

class GamePresets:
    def __init__(self) -> None:
        self.map_size = 250.0
        self.game_mode = GameMode.MISSION_PLANNING
        self.attacking_drone_count = 1000
        self.defending_drone_count = 1000
        self.path_points = [(0.0, 0.0), (1.0, 1.0)]
        
        #AI
        self.ai_engage_distance: float = 300.0
        self.ai_agression_threshold: float = 0.6
        
        #Drone
        self.drone_max_speed: float = 20.0
        self.drone_perception_radius: float = 40.0
        self.drone_mode: DroneModes = DroneModes.ATTACK
        self.drone_shooting_range: float = 50.0
        self.drone_shooting_cooldown: float = 2.0
        self.drone_hit_radius: float = 2.0
        self.drone_max_health: float = 100.0
        self.fov_cosine: float = 0.0 
        
        # Projectile
        self.projectile_speed: float = 50.0
        self.projectile_damage: float = 25.0
        self.projectile_max_lifetime: float = 1.0
        self.projectile_radius: float = 0.5
        
    def compare(self, other: "GamePresets") -> bool:
        if self.attacking_drone_count != other.attacking_drone_count:
            return False
        if self.defending_drone_count != other.defending_drone_count:
            return False
        return True
    
    def generate_config_dict(self) -> dict[str, tuple[Union[float, int, list[tuple[float, float]]], str]]:
        return {
            "map_size": (self.map_size, "Description: Map size, Data type: float, Range: (50, 1000), Default: 250.0"),
            "attacking_drone_count": (self.attacking_drone_count, "Description: Set attacking drone count, Data type: int, Range: (1, 8000), Default: 1000"),
            "defending_drone_count": (self.defending_drone_count, "Description: Set defending drone count, Data type: int, Range: (1, 8000), Default: 1000"),
            "path_points": (self.path_points, "Description: Set path points, Data type: list[tuple[float, float]], Range: (-1, 1), [(0.0, 0.0)]"),
            "ai_engage_distance": (self.ai_engage_distance, "Description: Set AI engage distance, Data type: float, Range: (0, 1000), Default: 300.0"),
            "ai_agression_threshold": (self.ai_agression_threshold, "Description: Set AI aggression threshold, Data type: float, Range: (0, 1), Default: 0.6"),
            "drone_max_speed": (self.drone_max_speed, "Description: Set drone max speed, Data type: float, Range: (1, 100), Default: 20.0"),
            "drone_shooting_range": (self.drone_shooting_range, "Description: Set drone shooting range, Data type: float, Range: (0, 1000), Default: 50.0"),
            "drone_shooting_cooldown": (self.drone_shooting_cooldown, "Description: Set drone shooting cooldown, Data type: float, Range: (0, inf), Default: 2.0"),
            "drone_max_health": (self.drone_max_health, "Description: Set drone max health, Data type: int, Range: (1, inf), Default: 100"),
            "drone_perception_radius": (self.drone_perception_radius, "Description: Set drone perception radius, Data type: float, Range: (0, 360), Default: 40.0"),
            "drone_hit_radius": (self.drone_hit_radius, "Description: Set drone hit radius, Data type: float, Range: (1, inf), Default: 2.0"),
            "projectile_damage": (self.projectile_damage, "Description: Set projectile damage, Data type: float, Range: (1, inf), Default: 25.0"),
            "projectile_radius": (self.projectile_radius, "Description: Set projectile radius, Data type: float, Range: (1, inf), Default: 0.5"),
            "projectile_max_lifetime": (self.projectile_max_lifetime, "Description: Set projectile max lifetime, Data type: float, Range: (0.1, inf), Default: 1.0")
        }
        
        
    def load_config(self, config: dict[str, tuple[tuple[float | int | tuple[float, float]], str]]) -> None:
        self.map_size = config["map_size"][0]
        self.attacking_drone_count = config["attacking_drone_count"][0]
        self.defending_drone_count = config["defending_drone_count"][0]
        self.path_points = config["path_points"][0]
        self.ai_engage_distance = config["ai_engage_distance"][0]
        self.ai_agression_threshold = config["ai_agression_threshold"][0]
        self.drone_max_speed = config["drone_max_speed"][0]
        self.drone_shooting_range = config["drone_shooting_range"][0]
        self.drone_shooting_cooldown = config["drone_shooting_cooldown"][0]
        self.drone_max_health = config["drone_max_health"][0]
        self.drone_perception_radius = config["drone_perception_radius"][0]
        self.drone_hit_radius = config["drone_hit_radius"][0]
        self.projectile_damage = config["projectile_damage"][0]
        self.projectile_radius = config["projectile_radius"][0]     
        self.projectile_max_lifetime = config["projectile_max_lifetime"][0]
        self.fov_cosine = config["fov_cosine"][0]