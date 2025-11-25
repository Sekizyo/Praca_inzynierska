from taichi import MatrixField, data_oriented, f32
import taichi as ti


class Map:
    def __init__(self, boundary: float = 100.0, height: float = 50.0):
        self.boundary: float = boundary
        self.height: float = height
        self.boundary_lines: MatrixField = ti.Vector.field(3, dtype=ti.f32, shape=24)
        self.init_boundary_lines()

    def init_boundary_lines(self) -> None:
        B: float = self.boundary
        H: float = self.height
        lines = [
            [-B, -B, 0], [B, -B, 0], [B, -B, 0], [B, B, 0], [B, B, 0], [-B, B, 0], [-B, B, 0], [-B, -B, 0], # Bottom
            [-B, -B, H], [B, -B, H], [B, -B, H], [B, B, H], [B, B, H], [-B, B, H], [-B, B, H], [-B, -B, H], # Top
            [-B, -B, 0], [-B, -B, H], [B, -B, 0], [B, -B, H], [B, B, 0], [B, B, H], [-B, B, 0], [-B, B, H]  # Vertical
        ]
        for i in range(24):
            self.boundary_lines[i] = lines[i]
            
    
    def get_boundary_field(self):
        return self.boundary_lines