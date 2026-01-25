from typing import Optional
from modules.constants import GameMode

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
    def __init__(self, map_size: float, game_mode: GameMode, attacking_drone_count: int, defending_drone_count: int, path_points: list[tuple[float, float]], enemy_ai_params: EnemyAIParams) -> None:
        self.map_size = map_size
        self.game_mode = game_mode
        self.attacking_drone_count = attacking_drone_count
        self.defending_drone_count = defending_drone_count
        self.path_points = path_points
        self.enemy_ai_params = enemy_ai_params
        
    def compare(self, other: "GamePresets") -> bool:
        if self.attacking_drone_count != other.attacking_drone_count:
            return False
        if self.defending_drone_count != other.defending_drone_count:
            return False
        return True
    