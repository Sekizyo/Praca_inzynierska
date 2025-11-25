from taichi import MatrixField
import taichi as ti


class Map:
    def __init__(self, boundary: float = 100.0) -> None:
        self.boundary: float = boundary
        self.height: float = boundary
        self.boundary_lines: MatrixField = ti.Vector.field(3, dtype=ti.f32, shape=24)
        self.init_boundary_lines()

    def init_boundary_lines(self) -> None:
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
            
    
    def get_boundary_field(self) -> MatrixField:
        return self.boundary_lines