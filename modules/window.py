import taichi as ti
from modules.drone import DroneSwarm
from modules.map import Map
from modules.voronoi import VoronoiDiagram
from taichi.ui.window import Window as TWindow
from taichi.ui import Canvas,  Camera



class Window():
    PLAYER_COLOR = (1.0, 0.2, 0.2)
    ENEMY_COLOR = (0.2, 0.2, 1.0)
    BOURNDARY_COLOR = (0.0, 1.0, 0.0)
    BOURNDARY_WIDTH: float = 1.0
    TARGET_COLOR = (1.0, 1.0, 0.0)
    TARGET_RADIUS: float = 2.0
    
    def __init__(self, title="Drone Voronoi Sim", size=(1024, 768)):
        ti.init()
        self.window: TWindow = TWindow(title, size)
        self.canvas: Canvas = self.window.get_canvas()
        self.scene = self.window.get_scene()
        self.map = Map()
        self.camera: Camera = Camera()
        
        self._init_camera()
        self._init_swarms()
        
    def _init_camera(self) -> None:
        self.camera.position(0, 0, 300)
        self.camera.lookat(0, 0, 0)
        self.camera.up(0, 1, 0)
    
    def _init_swarms(self) -> None:
        self.player_swarm = DroneSwarm(count=10, boundary_size=100.0)
        # self.enemy_swarm = DroneSwarm(count=10, boundary_size=100.0)
        self.target = ti.Vector([0.0, 0.0])
        self.target_field = ti.Vector.field(3, dtype=ti.f32, shape=1)
        self.target_field[0] = [0.0, 0.0, 0.0]
        
        self.voronoi = VoronoiDiagram(boundary=100.0, resolution=200)
        
    def _handle_input(self) -> None:
        if self.window.is_pressed(ti.ui.LMB):
            mouse_pos = self.window.get_cursor_pos()
            x = (mouse_pos[0] - 0.5) * 200.0
            y = (mouse_pos[1] - 0.5) * 200.0
            self.target = ti.Vector([x, y])
            self.target_field[0] = [x, y, 0.0]
        
    def _update_camera(self) -> None:
        self.camera.track_user_inputs(self.window, movement_speed=1, hold_key=ti.ui.RMB)
        self.scene.set_camera(self.camera)
        self.scene.point_light(pos=(0, 0, 100), color=(1, 1, 1))
        
    def _update_swarms(self, target) -> None:
        self.player_swarm.update(dt=0.05, target_pos=target, mode_weight=1.5)
        self.scene.particles(self.player_swarm.get_pos_field(), color=self.PLAYER_COLOR, radius=1.0)
        # self.enemy_swarm.update(dt=0.05, target_pos=target, mode_weight=1.5)
        # self.scene.particles(self.enemy_swarm.get_pos_field(), color=self.ENEMY_COLOR, radius=1.0)
        
    def _update_bourndary(self) -> None:
        self.scene.lines(self.map.get_boundary_field(), color=self.BOURNDARY_COLOR, width=self.BOURNDARY_WIDTH)
    
    def _draw_target(self) -> None:
        self.scene.particles(self.target_field, color=self.TARGET_COLOR, radius=self.TARGET_RADIUS)
    
    def _draw_voronoi(self) -> None:
        self.voronoi.update(self.player_swarm.get_pos_field(), self.player_swarm.N)
        self.scene.mesh(self.voronoi.get_vertices(), per_vertex_color=self.voronoi.get_colors())
        
    def run(self) -> None:
        while self.window.running:
            self._handle_input()
            self._update_camera()
            self._update_bourndary()
            self._update_swarms(self.target)
            self._draw_voronoi()
            self._draw_target()
            self.canvas.scene(self.scene)
            self.window.show()
