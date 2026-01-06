import taichi as ti
from taichi import MatrixField, Field


@ti.data_oriented
class VoronoiDiagram:
    def __init__(self, boundary: float = 100.0, resolution: int = 100):
        self.boundary: float = boundary
        self.resolution: int = resolution
        
        self.num_cells = (resolution - 1) * (resolution - 1)
        self.num_triangles = self.num_cells * 2
        self.num_vertices = self.num_triangles * 3
        
        self.vertices = ti.Vector.field(3, dtype=ti.f32, shape=self.num_vertices)
        self.colors = ti.Vector.field(3, dtype=ti.f32, shape=self.num_vertices)
        
        self.player_cells = ti.field(dtype=ti.i32, shape=())
        self.total_cells = ti.field(dtype=ti.i32, shape=())
        self.total_cells[None] = self.num_cells
        
        self.player_color = ti.Vector([1.0, 0.2, 0.2])
        self.enemy_color = ti.Vector([0.2, 0.2, 1.0])

    
    @ti.kernel
    def compute_voronoi(self, player_pos: ti.template(), player_count: ti.i32, player_health: ti.template(), enemy_pos: ti.template(), enemy_count: ti.i32, enemy_health: ti.template()):
        res = self.resolution
        B = self.boundary
        
        self.player_cells[None] = 0
        res_minus_1 = res - 1
        inv_res = 1.0 / ti.cast(res_minus_1, ti.f32)
        
        for i, j in ti.ndrange(res_minus_1, res_minus_1):
            cell_idx = i * res_minus_1 + j
            tri_idx = cell_idx * 2
            vert_idx = tri_idx * 3
            
            i_f = ti.cast(i, ti.f32)
            j_f = ti.cast(j, ti.f32)
            
            x0 = (i_f * inv_res - 0.5) * 2.0 * B
            y0 = (j_f * inv_res - 0.5) * 2.0 * B
            x1 = ((i_f + 1.0) * inv_res - 0.5) * 2.0 * B
            y1 = ((j_f + 1.0) * inv_res - 0.5) * 2.0 * B
            
            cx = (x0 + x1) * 0.5
            cy = (y0 + y1) * 0.5
            
            min_dist_sq = 1e20
            is_player = 0
            
            for k in range(player_count):
                if player_health[k][0] != 0:
                    continue
                dx = player_pos[k].x - cx
                dy = player_pos[k].y - cy
                dist_sq = dx * dx + dy * dy
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    is_player = 1
            
            for k in range(enemy_count):
                if enemy_health[k][0] != 0:
                    continue
                dx = enemy_pos[k].x - cx
                dy = enemy_pos[k].y - cy
                dist_sq = dx * dx + dy * dy
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    is_player = 0
            
            color = self.player_color if is_player == 1 else self.enemy_color
            
            if is_player == 1:
                ti.atomic_add(self.player_cells[None], 1)
            
            self.vertices[vert_idx + 0] = [x0, y0, 0.1]
            self.vertices[vert_idx + 1] = [x1, y0, 0.1]
            self.vertices[vert_idx + 2] = [x1, y1, 0.1]
            
            self.vertices[vert_idx + 3] = [x0, y0, 0.1]
            self.vertices[vert_idx + 4] = [x1, y1, 0.1]
            self.vertices[vert_idx + 5] = [x0, y1, 0.1]
            
            for v in ti.static(range(6)):
                self.colors[vert_idx + v] = color
    
    def update(self, player_pos: MatrixField, player_count: int, player_health: Field, enemy_pos: MatrixField, enemy_count: int, enemy_health: Field) -> float:
        self.compute_voronoi(player_pos, player_count, player_health, enemy_pos, enemy_count, enemy_health)
        return (self.player_cells[None] / self.total_cells[None]) * 100.0
    
    def get_vertices(self) -> MatrixField:
        return self.vertices
    
    def get_colors(self) -> MatrixField:
        return self.colors
