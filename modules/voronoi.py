import taichi as ti
from taichi import MatrixField


@ti.data_oriented
class VoronoiDiagram:
    def __init__(self, boundary: float = 100.0, resolution: int = 100):
        self.boundary: float = boundary
        self.resolution: int = resolution
        
        # Number of triangles: 2 per grid cell
        # Grid is (resolution x resolution), so (resolution-1)^2 cells
        self.num_cells = (resolution - 1) * (resolution - 1)
        self.num_triangles = self.num_cells * 2
        self.num_vertices = self.num_triangles * 3
        
        # Vertices for rendering the plane as triangles
        self.vertices = ti.Vector.field(3, dtype=ti.f32, shape=self.num_vertices)
        self.colors = ti.Vector.field(3, dtype=ti.f32, shape=self.num_vertices)
        
        # Predefined colors for different drones
        self.drone_colors = ti.Vector.field(3, dtype=ti.f32, shape=20)
        self._init_colors()
    
    def _init_colors(self) -> None:
        colors = [
            [1.0, 0.2, 0.2],  # Red
            [0.2, 1.0, 0.2],  # Green
            [0.2, 0.2, 1.0],  # Blue
            [1.0, 1.0, 0.2],  # Yellow
            [1.0, 0.2, 1.0],  # Magenta
            [0.2, 1.0, 1.0],  # Cyan
            [1.0, 0.5, 0.2],  # Orange
            [0.5, 0.2, 1.0],  # Purple
            [0.2, 1.0, 0.5],  # Mint
            [1.0, 0.2, 0.5],  # Pink
            [0.8, 0.8, 0.2],  # Olive
            [0.2, 0.8, 0.8],  # Teal
            [0.8, 0.2, 0.8],  # Violet
            [0.6, 0.4, 0.2],  # Brown
            [0.4, 0.6, 0.8],  # Sky
            [0.8, 0.6, 0.4],  # Tan
            [0.4, 0.8, 0.6],  # Sea green
            [0.6, 0.8, 0.4],  # Lime
            [0.8, 0.4, 0.6],  # Rose
            [0.4, 0.4, 0.8],  # Slate
        ]
        for i in range(20):
            self.drone_colors[i] = colors[i]
    
    @ti.kernel
    def compute_voronoi(self, drone_pos: ti.template(), drone_count: ti.i32):
        res = self.resolution
        B = self.boundary
        
        for i, j in ti.ndrange(res - 1, res - 1):
            cell_idx = i * (res - 1) + j
            tri_idx = cell_idx * 2
            vert_idx = tri_idx * 3
            
            # Grid points
            x0 = (ti.cast(i, ti.f32) / (res - 1) - 0.5) * 2.0 * B
            y0 = (ti.cast(j, ti.f32) / (res - 1) - 0.5) * 2.0 * B
            x1 = (ti.cast(i + 1, ti.f32) / (res - 1) - 0.5) * 2.0 * B
            y1 = (ti.cast(j + 1, ti.f32) / (res - 1) - 0.5) * 2.0 * B
            
            # Find closest drone for center of cell
            cx = (x0 + x1) * 0.5
            cy = (y0 + y1) * 0.5
            
            min_dist = ti.cast(1e10, ti.f32)
            closest_idx = 0
            
            for k in range(drone_count):
                dx = drone_pos[k].x - cx
                dy = drone_pos[k].y - cy
                dist = ti.sqrt(dx * dx + dy * dy)
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = k
            
            color = self.drone_colors[closest_idx % 20]
            
            # Triangle 1: bottom-left triangle
            self.vertices[vert_idx + 0] = [x0, y0, 0.1]
            self.vertices[vert_idx + 1] = [x1, y0, 0.1]
            self.vertices[vert_idx + 2] = [x1, y1, 0.1]
            
            # Triangle 2: top-right triangle
            self.vertices[vert_idx + 3] = [x0, y0, 0.1]
            self.vertices[vert_idx + 4] = [x1, y1, 0.1]
            self.vertices[vert_idx + 5] = [x0, y1, 0.1]
            
            # Set colors
            for v in range(6):
                self.colors[vert_idx + v] = color
    
    def update(self, drone_pos: MatrixField, drone_count: int) -> None:
        self.compute_voronoi(drone_pos, drone_count)
    
    def get_vertices(self) -> MatrixField:
        return self.vertices
    
    def get_colors(self) -> MatrixField:
        return self.colors
