from taichi import MatrixField
import taichi as ti
from taichi.ui.scene import SceneV2

from modules.colors import BOURNDARY_COLOR

class Map:
    def __init__(self, scene: SceneV2, boundary: float) -> None:
        self.scene: SceneV2 = scene
        self.boundary: float = boundary
        self.height: float = boundary
        self.boundary_lines: MatrixField = ti.Vector.field(3, dtype=ti.f32, shape=24)
        self._init_boundary_lines()

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