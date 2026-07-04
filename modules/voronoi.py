import taichi as ti
from taichi import MatrixField, Field


@ti.data_oriented
class VoronoiDiagram:
    def __init__(self, boundary: float = 100.0, resolution: int = 100):
        self.boundary: float = boundary
        self.resolution: int = resolution
        
        self.num_cells: int = (resolution - 1) * (resolution - 1)
        self.num_triangles: int = self.num_cells * 2
        self.num_vertices: int = self.num_triangles * 3
        
        self.vertices = ti.Vector.field(3, dtype=ti.f32, shape=self.num_vertices)
        self.colors = ti.Vector.field(3, dtype=ti.f32, shape=self.num_vertices)
        
        self.player_cells = ti.field(dtype=ti.i32, shape=())
        self.total_cells = ti.field(dtype=ti.i32, shape=())
        self.total_cells[None] = self.num_cells
        
        self.territory_ratio = ti.field(dtype=ti.f32, shape=())
        self.cached_ratio = 50.0 
        
    def reset(self):
        self.cached_ratio = 50.0

    @ti.kernel
    def compute_voronoi(self, player_pos: ti.template(), player_count: ti.i32, player_health: ti.template(), enemy_pos: ti.template(), enemy_count: ti.i32, enemy_health: ti.template()):
        player_color = ti.Vector([1.0, 0.5, 0.5])
        enemy_color = ti.Vector([0.5, 0.5, 1.0])
        
        res = self.resolution
        self.player_cells[None] = 0
        
        res_minus_1 = res - 1
        inv_res = 1.0 / ti.cast(res_minus_1, ti.f32)
        cell_size = inv_res * 2.0 * self.boundary
        boundary_2 = 2.0 * self.boundary
        
        for i, j in ti.ndrange(res_minus_1, res_minus_1):
            grid_pos = ti.cast(ti.Vector([i, j]), ti.f32)
            base_pos = (grid_pos * inv_res - 0.5) * boundary_2
            
            x0, y0 = base_pos.x, base_pos.y
            x1, y1 = x0 + cell_size, y0 + cell_size
            center = ti.Vector([(x0 + x1) * 0.5, (y0 + y1) * 0.5])
            
            # Find closest owner
            min_dist_sq = 1e20
            is_player = 0
            
            for k in range(player_count):
                if player_health[k][0] > 0:
                    dist_sq = (player_pos[k].xy - center).norm_sqr()
                    if dist_sq < min_dist_sq:
                        min_dist_sq = dist_sq
                        is_player = 1
            
            for k in range(enemy_count):
                if enemy_health[k][0] > 0:
                    dist_sq = (enemy_pos[k].xy - center).norm_sqr()
                    if dist_sq < min_dist_sq:
                        min_dist_sq = dist_sq
                        is_player = 0
            
            if is_player == 0:
                ti.atomic_add(self.player_cells[None], 1)
            
            # Update vertices
            vert_idx = (i * res_minus_1 + j) * 6
            color = player_color if is_player else enemy_color
            
            self.vertices[vert_idx + 0] = [x0, y0, 0.1]
            self.vertices[vert_idx + 1] = [x1, y0, 0.1]
            self.vertices[vert_idx + 2] = [x1, y1, 0.1]
            
            self.vertices[vert_idx + 3] = [x0, y0, 0.1]
            self.vertices[vert_idx + 4] = [x1, y1, 0.1]
            self.vertices[vert_idx + 5] = [x0, y1, 0.1]
            
            for v in ti.static(range(6)):
                self.colors[vert_idx + v] = color
        
        self.territory_ratio[None] = (self.player_cells[None] / self.total_cells[None]) * 100.0
    
    def update(self, player_pos: MatrixField, player_count: int, player_health: Field, enemy_pos: MatrixField, enemy_count: int, enemy_health: Field) -> None:
        self.compute_voronoi(player_pos, player_count, player_health, enemy_pos, enemy_count, enemy_health)
    
    def pull_stats(self):
        self.cached_ratio = self.territory_ratio[None]

    def get_territory_ratio(self) -> float:
        return self.cached_ratio
    
    def get_vertices(self) -> MatrixField:
        return self.vertices
    
    def get_colors(self) -> MatrixField:
        return self.colors
