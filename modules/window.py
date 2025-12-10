import taichi as ti
from modules.drone import DroneSwarm, DroneModes
from modules.map import Map
from modules.voronoi import VoronoiDiagram
from taichi.ui.window import Window as TWindow
from taichi.ui import Canvas, Camera



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
        self.gui = self.window.get_gui()
        self.map_size: float = 250.0
        self.map = Map(self.map_size)
        self.camera: Camera = Camera()
        
        # GUI state
        self.paused: bool = False
        self.show_voronoi: bool = True
        self.show_boundary: bool = True
        self.drone_count: int = 10
        self.mode_weight: float = 1.5
        self.dt: float = 0.05
        
        
        self._init_camera()
        self._init_swarms()
        
    def _init_camera(self) -> None:
        self.camera.position(0, 0, self.map_size)
        self.camera.lookat(0, 0, 0)
        self.camera.up(0, 1, 0)
    
    def _init_swarms(self) -> None:
        self.player_swarm = DroneSwarm(count=self.drone_count, boundary_size=self.map_size)
        # self.enemy_swarm = DroneSwarm(count=self.drone_count, boundary_size=self.map_size)
        self.target = ti.Vector([0.0, 0.0])
        self.target_field = ti.Vector.field(3, dtype=ti.f32, shape=1)
        self.target_field[0] = [0.0, 0.0, 0.0]
        
        self.voronoi = VoronoiDiagram(boundary=self.map_size, resolution=200)
        
    def _handle_input(self) -> None:
        self.window.get_event()
        if self.window.is_pressed("q"):
            print("1 pressed")
            self.player_swarm.update_mode(DroneModes.ATTACK)
        elif self.window.is_pressed("e"):
            print("2 pressed")
            self.player_swarm.update_mode(DroneModes.SPREAD)
        elif self.window.is_pressed("r"):
            print("3 pressed")
            self.player_swarm.update_mode(DroneModes.PATROL)

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
        if self.show_boundary:
            self.scene.lines(self.map.get_boundary_field(), color=self.BOURNDARY_COLOR, width=self.BOURNDARY_WIDTH)
    
    def _draw_target(self) -> None:
        self.scene.particles(self.target_field, color=self.TARGET_COLOR, radius=self.TARGET_RADIUS)
    
    def _draw_voronoi(self) -> None:
        if self.show_voronoi:
            self.voronoi.update(self.player_swarm.get_pos_field(), self.player_swarm.N)
            self.scene.mesh(self.voronoi.get_vertices(), per_vertex_color=self.voronoi.get_colors())
    
    def _draw_gui(self) -> None:
        with self.gui.sub_window("Controls", 0.01, 0.01, 0.25, 0.4):
            # Pause button
            if self.gui.button("Pause" if not self.paused else "Resume"):
                self.paused = not self.paused
            

            # Toggles
            self.show_voronoi = self.gui.checkbox("Show Voronoi", self.show_voronoi)
            self.show_boundary = self.gui.checkbox("Show Boundary", self.show_boundary)
            
            # Sliders
            self.gui.text("Simulation Speed")
            self.dt = self.gui.slider_float("dt", self.dt, 0.01, 0.2)
            
            self.gui.text("Target Weight")
            self.mode_weight = self.gui.slider_float("weight", self.mode_weight, 0.0, 5.0)
            
            # Info
            self.gui.text(f"Drones: {self.player_swarm.N}")
            self.gui.text(f"Target: ({self.target[0]:.1f}, {self.target[1]:.1f})")
            self.gui.text(f"Mode: {self.player_swarm.get_mode()}")
            self.gui.text(f"Modifiers: {self.player_swarm.get_modifiers()}")
            

    def run(self) -> None:
        while self.window.running:
            self._handle_input()
            self._update_camera()
            
            
            if not self.paused:
                self.player_swarm.update(dt=self.dt, target_pos=self.target, mode_weight=self.mode_weight)
            
            self.scene.particles(self.player_swarm.get_pos_field(), color=self.PLAYER_COLOR, radius=1.0)
            self._update_bourndary()
            self._draw_voronoi()
            self._draw_target()
            self._draw_gui()
            
            self.canvas.scene(self.scene)
            self.window.show()
