from taichi import MatrixField
import taichi as ti
from taichi.ui.scene import SceneV2

from modules.colors import BOURNDARY_COLOR

class Map:
    def __init__(self, scene: SceneV2, presets) -> None:
        self.scene: SceneV2 = scene
        self.presets = presets
        self.boundary: float = presets.map_size
        self.height: float = presets.map_size
        self.boundary_lines: MatrixField = ti.Vector.field(3, dtype=ti.f32, shape=24)
        
        self.obstacle_count: int = presets.obstacle_count
        self.obstacle_pos: MatrixField = ti.Vector.field(3, dtype=ti.f32, shape=max(1, self.obstacle_count))
        self.obstacle_radius = ti.field(dtype=ti.f32, shape=max(1, self.obstacle_count))
        
        self._init_boundary_lines()
        self._init_obstacles()

    def _init_obstacles(self) -> None:
        import random
        if self.obstacle_count == 0:
            self.obstacle_pos[0] = ti.Vector([0.0, 0.0, -10000.0])
            self.obstacle_radius[0] = 0.0
            return
            
        for i in range(self.obstacle_count):
            x = random.uniform(-self.boundary + 50, self.boundary - 50)
            y = random.uniform(-self.boundary + 50, self.boundary - 50)
            z = random.uniform(50, self.height - 50)
            
            r = random.uniform(self.presets.obstacle_min_radius, self.presets.obstacle_max_radius)
            
            self.obstacle_pos[i] = ti.Vector([x, y, z])
            self.obstacle_radius[i] = r

    def _init_boundary_lines(self) -> None:
        B: float = self.boundary
        H: float = self.height
        lines = [
            # Bottom square
            [-B, -B, 0], [B, -B, 0],
            [B, -B, 0], [B, B, 0],
            [B, B, 0], [-B, B, 0],
            [-B, B, 0], [-B, -B, 0],
            # Top square
            [-B, -B, H], [B, -B, H],
            [B, -B, H], [B, B, H],
            [B, B, H], [-B, B, H],
            [-B, B, H], [-B, -B, H],
            # Vertical edges
            [-B, -B, 0], [-B, -B, H],
            [B, -B, 0], [B, -B, H],
            [B, B, 0], [B, B, H],
            [-B, B, 0], [-B, B, H]
        ]
        for i in range(24):
            self.boundary_lines[i] = lines[i]
            
    def draw_boundary(self) -> None:
        self.scene.lines(self.boundary_lines, color=BOURNDARY_COLOR, width=1.0)
        
    def draw_obstacles(self) -> None:
        if self.obstacle_count > 0:
            self.scene.particles(self.obstacle_pos, radius=1.0, color=(0.4, 0.4, 0.4), per_vertex_radius=self.obstacle_radius)