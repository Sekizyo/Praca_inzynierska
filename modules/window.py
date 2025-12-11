import taichi as ti
from modules.drone import DroneSwarm, DroneModes
from modules.map import Map
from modules.voronoi import VoronoiDiagram
from taichi.ui.window import Window as TWindow
from taichi.ui import Canvas, Camera
from modules.colors import PLAYER_COLOR, ENEMY_COLOR, BOURNDARY_COLOR, TARGET_COLOR, PROJECTILE_COLOR


class Window():
    BOURNDARY_WIDTH: float = 1.0
    TARGET_RADIUS: float = 3.0
    PROJECTILE_RADIUS: float = 0.5
    
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
        self.show_voronoi: bool = False
        self.show_boundary: bool = True
        self.drone_count: int = 20
        self.dt: float = 0.05
        self.player_territory: float = 0.0
        
        
        self._init_camera()
        self._init_swarms()
        
    def _init_camera(self) -> None:
        self.camera.position(0, 0, self.map_size*2)
        self.camera.lookat(0, 0, 0)
        self.camera.up(0, 1, 0)
    
    def _init_swarms(self) -> None:
        self.player_swarm = DroneSwarm(count=self.drone_count, boundary_size=self.map_size, team=0)
        self.enemy_swarm = DroneSwarm(count=self.drone_count, boundary_size=self.map_size, team=1)
        self.target = ti.Vector([0.0, 0.0])
        self.target_field = ti.Vector.field(3, dtype=ti.f32, shape=1)
        self.target_field[0] = [0.0, 0.0, 0.0]
        
        self.voronoi = VoronoiDiagram(boundary=self.map_size, resolution=200)
        
    def _handle_input(self) -> None:
        self.window.get_event()
        if self.window.is_pressed("q"):
            self.player_swarm.update_mode(DroneModes.ATTACK)
        elif self.window.is_pressed("e"):
            self.player_swarm.update_mode(DroneModes.SPREAD)
        elif self.window.is_pressed("r"):
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
        
    def _update_bourndary(self) -> None:
        if self.show_boundary:
            self.scene.lines(self.map.get_boundary_field(), color=BOURNDARY_COLOR, width=self.BOURNDARY_WIDTH)
    
    def _draw_target(self) -> None:
        self.scene.particles(self.target_field, color=TARGET_COLOR, radius=self.TARGET_RADIUS)
    
    def _draw_voronoi(self) -> None:
        self.player_territory = self.voronoi.update(
            self.player_swarm.get_pos_field(), 
            self.player_swarm.N,
            self.player_swarm.health,
            self.enemy_swarm.get_pos_field(),
            self.enemy_swarm.N,
            self.enemy_swarm.health
        )
        if self.show_voronoi:
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
            
            # Info
            self.gui.text(f"Drones: {self.player_swarm.N}")
            self.gui.text(f"Target: ({self.target[0]:.1f}, {self.target[1]:.1f})")
            self.gui.text(f"Mode: {self.player_swarm.get_mode()}")
            self.gui.text(f"Modifiers: {self.player_swarm.get_modifiers()}")
            self.gui.text(f"Territory: {self.player_territory:.1f}%")
            

    def run(self) -> None:
        while self.window.running:
            self._handle_input()
            self._update_camera()
            
            if not self.paused:
                self.player_swarm.update(dt=self.dt, target_pos=self.target)
                self.enemy_swarm.update(dt=self.dt, target_pos=[250, 0])
                
                self.player_swarm.shoot(self.enemy_swarm.get_pos_field(), self.enemy_swarm.N, self.enemy_swarm.health)
                self.enemy_swarm.shoot(self.player_swarm.get_pos_field(), self.player_swarm.N, self.player_swarm.health)
                
                self.player_swarm.update_projectiles(dt=self.dt)
                self.enemy_swarm.update_projectiles(dt=self.dt)
                
                self.player_swarm.check_hits(self.enemy_swarm.get_pos_field(), self.enemy_swarm.N, self.enemy_swarm.health)
                self.enemy_swarm.check_hits(self.player_swarm.get_pos_field(), self.player_swarm.N, self.player_swarm.health)
                
                self.player_swarm.update_health()
                self.enemy_swarm.update_health()
            
            self.scene.particles(self.player_swarm.get_pos_field(), color=PLAYER_COLOR, radius=1.0)
            self.scene.particles(self.enemy_swarm.get_pos_field(), color=ENEMY_COLOR, radius=1.0)
            
            self.scene.particles(self.player_swarm.get_projectile_pos_field(), color=PROJECTILE_COLOR, radius=self.PROJECTILE_RADIUS)
            self.scene.particles(self.enemy_swarm.get_projectile_pos_field(), color=PROJECTILE_COLOR, radius=self.PROJECTILE_RADIUS)
            
            self._update_bourndary()
            self._draw_voronoi()
            self._draw_target()
            self._draw_gui()
            
            self.canvas.scene(self.scene)
            self.window.show()
