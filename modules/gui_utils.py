from modules.constants import GameMode, DroneModes
class GuiState(str):
    def __init__(self) -> None:
        self.PAUSED: bool = False
        self.SHOW_VORONOI: bool = False
        self.SHOW_BOUNDARY: bool = True

class GamePresets:
    def __init__(self) -> None:
        self.map_size: int = 500
        self.game_mode = GameMode.MISSION_PLANNING
        self.attacking_drone_count: int = 1000
        self.defending_drone_count: int = 1000
        self.random_seed: int = 42
        
        # Obstacles
        self.obstacle_count: int = 20
        self.obstacle_min_radius: int = 5
        self.obstacle_max_radius: int = 25
        
        #AI
        self.ai_engage_distance: int = 150
        self.ai_agression_threshold: float = 0.6
        self.ai_evaluate_state: int = 15
        self.ai_execute_state: int = 20
        self.ai_path: list[tuple[float, float, float]] = []
        self.ai_path_normalized: list[tuple[float, float, float, DroneModes | None]] = self.normalize_to_world_coordinates(self.ai_path)
        self.fog_of_war: bool = False
        self.fog_of_war_radius: int = 0
        
        # Attacking Boids
        self.att_boids_attack_separation: float = 2.0
        self.att_boids_attack_alignment: float = 2.0
        self.att_boids_attack_cohesion: float = 1.5
        self.att_boids_attack_target: float = 2.0
        
        self.att_boids_spread_separation: float = 2.0
        self.att_boids_spread_alignment: float = 0.7
        self.att_boids_spread_cohesion: float = 0.3
        self.att_boids_spread_target: float = 1.0
        
        self.att_boids_patrol_separation: float = 2.0
        self.att_boids_patrol_alignment: float = 0.7
        self.att_boids_patrol_cohesion: float = 0.3
        self.att_boids_patrol_target: float = 1.0
        
        # Defending Boids
        self.def_boids_attack_separation: float = 2.0
        self.def_boids_attack_alignment: float = 2.0
        self.def_boids_attack_cohesion: float = 1.5
        self.def_boids_attack_target: float = 2.0
        
        self.def_boids_spread_separation: float = 2.0
        self.def_boids_spread_alignment: float = 0.7
        self.def_boids_spread_cohesion: float = 0.3
        self.def_boids_spread_target: float = 1.0
        
        self.def_boids_patrol_separation: float = 2.0
        self.def_boids_patrol_alignment: float = 0.7
        self.def_boids_patrol_cohesion: float = 0.3
        self.def_boids_patrol_target: float = 1.0
        
        #Drone
        self.attacking_path: list[tuple[float, float, float, DroneModes | None]] = []
        self.attacking_path_normalized: list[tuple[float, float, float, DroneModes | None]] = self.normalize_to_world_coordinates(self.attacking_path)
        self.drone_max_speed: int = 20
        self.drone_perception_radius: int = 120
        self.drone_shooting_perception_radius: float = 0.0
        self.drone_shooting_range: int = 50
        self.drone_shooting_cooldown: float = 2.0
        self.drone_hit_radius: int = 2
        self.drone_max_health: int = 100
        
        # Statistics
        self.stats_collection_frequency: int = 30
        self.position_collection_frequency: int = 30
        
        # Projectile
        self.projectile_speed: int = 50
        self.projectile_damage: int = 25
        self.projectile_max_lifetime: float = 2.0
        self.projectile_radius: int = 1
        
    def normalize_to_world_coordinates(self, points: list[tuple[float, float, float]] | list[tuple[float, float, float, DroneModes | None]] ) -> list[tuple[float, float, float, DroneModes | None]]:
        if not points:
            return []
        
        normalized = []
        for pt in points:
            if len(pt) == 3:
                x, y, z = pt
                normalized.append((x * self.map_size, y * self.map_size, z * self.map_size, None))
            elif len(pt) == 4:
                x, y, z, mode = pt
                normalized.append((x * self.map_size, y * self.map_size, z * self.map_size, mode))
        return normalized

    def compare(self, other: "GamePresets") -> bool:
        if self.attacking_drone_count != other.attacking_drone_count:
            return False
        if self.defending_drone_count != other.defending_drone_count:
            return False
        return True
    
    def generate_config_dict(self) -> dict[str, tuple[float | int | list, str]]:
        return {
            "map_size": (self.map_size, f"Type: int, Range: (50, 1000), Default: {self.map_size}"),
            "attacking_drone_count": (self.attacking_drone_count, f"Type: int, Range: (1, 8000), Default: {self.attacking_drone_count}"),
            "defending_drone_count": (self.defending_drone_count, f"Type: int, Range: (1, 8000), Default: {self.defending_drone_count}"),
            "random_seed": (self.random_seed, f"Type: int, Range: (0, 10000), Default: {self.random_seed}"),
            
            "obstacle_count": (self.obstacle_count, f"Type: int, Range: (0, 100), Default: {self.obstacle_count}"),
            "obstacle_min_radius": (self.obstacle_min_radius, f"Type: int, Range: (1, 50), Default: {self.obstacle_min_radius}"),
            "obstacle_max_radius": (self.obstacle_max_radius, f"Type: int, Range: (1, 50), Default: {self.obstacle_max_radius}"),
            
            "ai_path": (self.ai_path, f"Type: list[tuple[float, float, float]], Range: (-1, 1), Default: {self.ai_path}"),
            "ai_engage_distance": (self.ai_engage_distance, f"Type: int, Range: (0, map_size), Default: {self.ai_engage_distance}"),
            "ai_agression_threshold": (self.ai_agression_threshold, f"Type: float, Range: (0, 1), Default: {round(self.ai_agression_threshold, 2)}"),
            "ai_evaluate_state": (self.ai_evaluate_state, f"Type: int, Range: (1, 50), Default: {self.ai_evaluate_state}"),
            "ai_execute_state": (self.ai_execute_state, f"Type: int, Range: (1, 50), Default: {self.ai_execute_state}"),
            "fog_of_war": (self.fog_of_war, f"Type: bool, Default: {self.fog_of_war}"),
            "fog_of_war_radius": (self.fog_of_war_radius, f"Type: int, Range: (0, 10), Default: {self.fog_of_war_radius}"),
            
            "att_boids_attack_cohesion": (self.att_boids_attack_cohesion, f"Type: int, Range: (1, 10), Default: {self.att_boids_attack_cohesion}"),
            "att_boids_attack_separation": (self.att_boids_attack_separation, f"Type: int, Range: (1, 10), Default: {self.att_boids_attack_separation}"),
            "att_boids_attack_alignment": (self.att_boids_attack_alignment, f"Type: int, Range: (1, 10), Default: {self.att_boids_attack_alignment}"),
            "att_boids_attack_target": (self.att_boids_attack_target, f"Type: int, Range: (1, 10), Default: {self.att_boids_attack_target}"),
            
            "att_boids_spread_cohesion": (self.att_boids_spread_cohesion, f"Type: int, Range: (1, 10), Default: {self.att_boids_spread_cohesion}"),
            "att_boids_spread_separation": (self.att_boids_spread_separation, f"Type: int, Range: (1, 10), Default: {self.att_boids_spread_separation}"),
            "att_boids_spread_alignment": (self.att_boids_spread_alignment, f"Type: int, Range: (1, 10), Default: {self.att_boids_spread_alignment}"),
            "att_boids_spread_target": (self.att_boids_spread_target, f"Type: int, Range: (1, 10), Default: {self.att_boids_spread_target}"),
            
            "att_boids_patrol_cohesion": (self.att_boids_patrol_cohesion, f"Type: int, Range: (1, 10), Default: {self.att_boids_patrol_cohesion}"),
            "att_boids_patrol_separation": (self.att_boids_patrol_separation, f"Type: int, Range: (1, 10), Default: {self.att_boids_patrol_separation}"),
            "att_boids_patrol_alignment": (self.att_boids_patrol_alignment, f"Type: int, Range: (1, 10), Default: {self.att_boids_patrol_alignment}"),
            "att_boids_patrol_target": (self.att_boids_patrol_target, f"Type: int, Range: (1, 10), Default: {self.att_boids_patrol_target}"),

            "def_boids_attack_cohesion": (self.def_boids_attack_cohesion, f"Type: int, Range: (1, 10), Default: {self.def_boids_attack_cohesion}"),
            "def_boids_attack_separation": (self.def_boids_attack_separation, f"Type: int, Range: (1, 10), Default: {self.def_boids_attack_separation}"),
            "def_boids_attack_alignment": (self.def_boids_attack_alignment, f"Type: int, Range: (1, 10), Default: {self.def_boids_attack_alignment}"),
            "def_boids_attack_target": (self.def_boids_attack_target, f"Type: int, Range: (1, 10), Default: {self.def_boids_attack_target}"),
            
            "def_boids_spread_cohesion": (self.def_boids_spread_cohesion, f"Type: int, Range: (1, 10), Default: {self.def_boids_spread_cohesion}"),
            "def_boids_spread_separation": (self.def_boids_spread_separation, f"Type: int, Range: (1, 10), Default: {self.def_boids_spread_separation}"),
            "def_boids_spread_alignment": (self.def_boids_spread_alignment, f"Type: int, Range: (1, 10), Default: {self.def_boids_spread_alignment}"),
            "def_boids_spread_target": (self.def_boids_spread_target, f"Type: int, Range: (1, 10), Default: {self.def_boids_spread_target}"),
            
            "def_boids_patrol_cohesion": (self.def_boids_patrol_cohesion, f"Type: int, Range: (1, 10), Default: {self.def_boids_patrol_cohesion}"),
            "def_boids_patrol_separation": (self.def_boids_patrol_separation, f"Type: int, Range: (1, 10), Default: {self.def_boids_patrol_separation}"),
            "def_boids_patrol_alignment": (self.def_boids_patrol_alignment, f"Type: int, Range: (1, 10), Default: {self.def_boids_patrol_alignment}"),
            "def_boids_patrol_target": (self.def_boids_patrol_target, f"Type: int, Range: (1, 10), Default: {self.def_boids_patrol_target}"),
            
            "drone_path": (self.attacking_path, f"Type: list[tuple[float, float, float, 'attack' | 'spread']], Range: (-1, 1), Default: {self.attacking_path}"),
            "drone_max_speed": (self.drone_max_speed, f"Type: int, Range: (1, 100), Default: {self.drone_max_speed}"),
            "drone_shooting_range": (self.drone_shooting_range, f"Type: int, Range: (0, map_size), Default: {self.drone_shooting_range}"),
            "drone_shooting_cooldown": (self.drone_shooting_cooldown, f"Type: int, Range: (0, 100), Default: {self.drone_shooting_cooldown}"),
            "drone_max_health": (self.drone_max_health, f"Type: int, Range: (1, 100), Default: {self.drone_max_health}"),
            "drone_perception_radius": (self.drone_perception_radius, f"Type: int, Range: (0, 360), Default: {self.drone_perception_radius}"),
            "drone_shooting_perception_radius": (self.drone_shooting_perception_radius, f"Type: int, Range: (0, 360), Default: {self.drone_shooting_perception_radius}"),
            "drone_hit_radius": (self.drone_hit_radius, f"Type: int, Range: (1, 5), Default: {self.drone_hit_radius}"),
            
            "stats_collection_frequency": (self.stats_collection_frequency, f"Type: int, Range: (1, 300), Default: {self.stats_collection_frequency}"),
            "position_collection_frequency": (self.position_collection_frequency, f"Type: int, Range: (1, 600), Default: {self.position_collection_frequency}"),

            "projectile_damage": (self.projectile_damage, f"Type: int, Range: (1, drone_max_health), Default: {self.projectile_damage}"),
            "projectile_radius": (self.projectile_radius, f"Type: int, Range: (1, 5), Default: {self.projectile_radius}"),
            "projectile_max_lifetime": (self.projectile_max_lifetime, f"Type: float, Range: (0.5, 10), Default: {self.projectile_max_lifetime}")
        }
        
    def load_config(self, config: dict | None) -> None:
        if not config:
            return
        
        self.map_size = int(config.get("map_size", self.map_size))
        self.attacking_drone_count = int(config.get("attacking_drone_count", self.attacking_drone_count))
        self.defending_drone_count = int(config.get("defending_drone_count", self.defending_drone_count))
        self.random_seed = int(config.get("random_seed", self.random_seed))
        
        self.obstacle_count = int(config.get("obstacle_count", self.obstacle_count))
        self.obstacle_min_radius = int(config.get("obstacle_min_radius", self.obstacle_min_radius))
        self.obstacle_max_radius = int(config.get("obstacle_max_radius", self.obstacle_max_radius))
        
        self.ai_path = config.get("ai_path", self.ai_path)
        self.ai_path_normalized = self.normalize_to_world_coordinates(self.ai_path)
        self.fog_of_war = bool(config.get("fog_of_war", self.fog_of_war))
        self.fog_of_war_radius = int(config.get("fog_of_war_radius", self.fog_of_war_radius))
        self.ai_engage_distance = int(config.get("ai_engage_distance", self.ai_engage_distance))
        self.ai_agression_threshold = float(round(float(config.get("ai_agression_threshold", self.ai_agression_threshold)), 2))
        self.ai_evaluate_state = int(config.get("ai_evaluate_state", self.ai_evaluate_state))
        self.ai_execute_state = int(config.get("ai_execute_state", self.ai_execute_state))
        
        
        self.att_boids_attack_separation = float(config.get("att_boids_attack_separation", self.att_boids_attack_separation))
        self.att_boids_attack_alignment = float(config.get("att_boids_attack_alignment", self.att_boids_attack_alignment))
        self.att_boids_attack_cohesion = float(config.get("att_boids_attack_cohesion", self.att_boids_attack_cohesion))
        self.att_boids_attack_target = float(config.get("att_boids_attack_target", self.att_boids_attack_target))

        self.att_boids_spread_separation = float(config.get("att_boids_spread_separation", self.att_boids_spread_separation))  
        self.att_boids_spread_alignment = float(config.get("att_boids_spread_alignment", self.att_boids_spread_alignment))
        self.att_boids_spread_cohesion = float(config.get("att_boids_spread_cohesion", self.att_boids_spread_cohesion))
        self.att_boids_spread_target = float(config.get("att_boids_spread_target", self.att_boids_spread_target))

        self.att_boids_patrol_separation = float(config.get("att_boids_patrol_separation", self.att_boids_patrol_separation))
        self.att_boids_patrol_alignment = float(config.get("att_boids_patrol_alignment", self.att_boids_patrol_alignment))
        self.att_boids_patrol_cohesion = float(config.get("att_boids_patrol_cohesion", self.att_boids_patrol_cohesion))
        self.att_boids_patrol_target = float(config.get("att_boids_patrol_target", self.att_boids_patrol_target))

        self.def_boids_attack_separation = float(config.get("def_boids_attack_separation", self.def_boids_attack_separation))
        self.def_boids_attack_alignment = float(config.get("def_boids_attack_alignment", self.def_boids_attack_alignment))
        self.def_boids_attack_cohesion = float(config.get("def_boids_attack_cohesion", self.def_boids_attack_cohesion))
        self.def_boids_attack_target = float(config.get("def_boids_attack_target", self.def_boids_attack_target))

        self.def_boids_spread_separation = float(config.get("def_boids_spread_separation", self.def_boids_spread_separation))  
        self.def_boids_spread_alignment = float(config.get("def_boids_spread_alignment", self.def_boids_spread_alignment))
        self.def_boids_spread_cohesion = float(config.get("def_boids_spread_cohesion", self.def_boids_spread_cohesion))
        self.def_boids_spread_target = float(config.get("def_boids_spread_target", self.def_boids_spread_target))

        self.def_boids_patrol_separation = float(config.get("def_boids_patrol_separation", self.def_boids_patrol_separation))
        self.def_boids_patrol_alignment = float(config.get("def_boids_patrol_alignment", self.def_boids_patrol_alignment))
        self.def_boids_patrol_cohesion = float(config.get("def_boids_patrol_cohesion", self.def_boids_patrol_cohesion))
        self.def_boids_patrol_target = float(config.get("def_boids_patrol_target", self.def_boids_patrol_target))

        self.attacking_path = config.get("drone_path", self.attacking_path)
        self.attacking_path_normalized = self.normalize_to_world_coordinates(self.attacking_path)
        self.drone_max_speed = int(config.get("drone_max_speed", self.drone_max_speed))
        self.drone_shooting_range = int(config.get("drone_shooting_range", self.drone_shooting_range))
        self.drone_shooting_cooldown = float(config.get("drone_shooting_cooldown", self.drone_shooting_cooldown))
        self.drone_max_health = int(config.get("drone_max_health", self.drone_max_health))
        self.drone_perception_radius = int(config.get("drone_perception_radius", self.drone_perception_radius))
        self.drone_shooting_perception_radius = float(config.get("drone_shooting_perception_radius", self.drone_shooting_perception_radius))
        self.drone_hit_radius = int(config.get("drone_hit_radius", self.drone_hit_radius))
        
        self.stats_collection_frequency = int(config.get("stats_collection_frequency", self.stats_collection_frequency))
        self.position_collection_frequency = int(config.get("position_collection_frequency", self.position_collection_frequency))

        self.projectile_damage = int(config.get("projectile_damage", self.projectile_damage))
        self.projectile_radius = int(config.get("projectile_radius", self.projectile_radius))
        self.projectile_max_lifetime = float(config.get("projectile_max_lifetime", self.projectile_max_lifetime))