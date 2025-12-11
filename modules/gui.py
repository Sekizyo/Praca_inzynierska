from taichi.ui.scene import SceneV2
from taichi.ui.window import Window as TWindow
from taichi.ui.ui import Gui
from taichi.ui import Camera, LMB, RMB
import taichi as ti 
from modules.map import Map
from modules.swarms import Swarms
from modules.constants import DroneModes
from modules.voronoi import VoronoiDiagram


class GUI():
    MAP_SIZE: float = 100.0
    
    def __init__(self, gui: Gui, window: TWindow, scene: SceneV2) -> None:
        self.gui = gui
        self.window = window
        self.scene = scene
        
        self.paused: bool = False
        self.show_voronoi: bool = False
        self.show_boundary: bool = True
        
        self.dt: float = 0.05
        self.drone_count: int = 20
        self.player_territory: float = 0.0
        
        self.swarms: Swarms = Swarms(self.scene, self.drone_count, self.MAP_SIZE)
        self.map = Map(self.scene, self.MAP_SIZE)
        
        self.voronoi = VoronoiDiagram(boundary=self.MAP_SIZE, resolution=200)

        self._init_camera()
        
    def _init_camera(self) -> None:
        self.camera: Camera = Camera()
        self.camera.position(0, 0, 500)
        self.camera.lookat(0, 0, 0)
        self.camera.up(0, 1, 0)
        
    def _update_camera(self) -> None:
        self.camera.track_user_inputs(self.window, movement_speed=1, hold_key=RMB)
        self.scene.set_camera(self.camera)
        self.scene.point_light(pos=(0, 0, 100), color=(1, 1, 1))
        
    def _handle_input(self) -> None:
        self.window.get_event()
        if self.window.is_pressed("q"):
            self.swarms.get_player_swarm().update_mode(DroneModes.ATTACK)
        elif self.window.is_pressed("e"):
            self.swarms.get_player_swarm().update_mode(DroneModes.SPREAD)
        elif self.window.is_pressed("r"):
            self.swarms.get_player_swarm().update_mode(DroneModes.PATROL)

        if self.window.is_pressed(LMB):
            mouse_pos = self.window.get_cursor_pos()
            x = (mouse_pos[0] - 0.5) * 200.0
            y = (mouse_pos[1] - 0.5) * 200.0
            self.swarms.set_player_target(x, y)

        
    def _update_bourndary(self) -> None:
        if self.show_boundary:
            self.map.draw_boundary()
            
    def _update_gui(self) -> None:
        with self.gui.sub_window("Controls", 0.01, 0.01, 0.25, 0.4):
            if self.gui.button("Pause" if not self.paused else "Resume"):
                self.paused = not self.paused

            self.show_voronoi = self.gui.checkbox("Show Voronoi", self.show_voronoi)
            self.show_boundary = self.gui.checkbox("Show Boundary", self.show_boundary)
            
            self.gui.text(f"Drones: {self.swarms.get_player_swarm().N}")
            self.gui.text(f"Mode: {self.swarms.get_player_swarm().get_mode()}")
            self.gui.text(f"Modifiers: {self.swarms.get_player_swarm().get_modifiers()}")
            self.gui.text(f"Territory: {self.player_territory:.1f}%")
        
    def _draw_voronoi(self) -> None:
        player_swarm = self.swarms.get_player_swarm()
        enemy_swarm = self.swarms.get_enemy_swarm()
        
        self.player_territory = self.voronoi.update(
            player_swarm.get_pos_field(), 
            player_swarm.N,
            player_swarm.health,
            enemy_swarm.get_pos_field(),
            enemy_swarm.N,
            enemy_swarm.health
        )
        if self.show_voronoi:
            self.scene.mesh(self.voronoi.get_vertices(), per_vertex_color=self.voronoi.get_colors())
        
    def update(self) -> None:
        self._update_camera()
        self._update_bourndary()
        self._handle_input()
        
        if not self.paused:
            self.swarms.update(self.dt)
        
        self._draw_voronoi()
        self._update_gui()