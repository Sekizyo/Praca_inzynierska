from taichi.ui.scene import SceneV2
from taichi.ui.window import Window as TWindow
from taichi.ui.ui import Gui
from taichi.ui import Camera, LMB, RMB
from modules.map import Map
from modules.swarms import Swarms
from modules.constants import DroneModes
from modules.voronoi import VoronoiDiagram
from modules.gui_utils import GuiState
from modules.utils import run_every_n_calls

class GUI():
    MAP_SIZE: float = 400.0
    
    def __init__(self, gui: Gui, window: TWindow, scene: SceneV2) -> None:
        self.gui = gui
        self.window = window
        self.scene = scene
        self.GuiState: GuiState = GuiState()
        
        self.dt: float = 0.15
        self.drone_count: int = 200
        self.player_territory: float = 0.0
        
        self.swarms: Swarms = Swarms(self.scene, self.drone_count, self.MAP_SIZE)
        self.map = Map(self.scene, self.MAP_SIZE)
        
        self.voronoi = VoronoiDiagram(boundary=self.MAP_SIZE, resolution=100)

        self._init_camera()
        
    def _init_camera(self) -> None:
        self.camera: Camera = Camera()
        self.camera.position(0, 0, 500)
        self.camera.lookat(0, 0, 0)
        self.camera.up(0, 1, 0)
        
    def _update_camera(self) -> None:
        self.camera.track_user_inputs(self.window, movement_speed=3, hold_key=RMB)
        self.scene.set_camera(self.camera)
        self.scene.point_light(pos=(0, 0, self.MAP_SIZE), color=(1, 1, 1))
        
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
        if self.GuiState.SHOW_BOUNDARY:
            self.map.draw_boundary()
            
    def _update_gui(self) -> None:
        with self.gui.sub_window("Controls", 0.01, 0.01, 0.25, 0.4):
            if self.gui.button("Pause" if not self.GuiState.PAUSED else "Resume"):
                self.GuiState.PAUSED = not self.GuiState.PAUSED

            self.GuiState.SHOW_VORONOI = self.gui.checkbox("Show Voronoi", self.GuiState.SHOW_VORONOI)
            self.GuiState.SHOW_BOUNDARY = self.gui.checkbox("Show Boundary", self.GuiState.SHOW_BOUNDARY)
            self.GuiState.SHOW_SHOOT_RANGE = self.gui.checkbox("Show Shooting Range", self.GuiState.SHOW_SHOOT_RANGE)
            
            player_swarm = self.swarms.get_player_swarm()
            enemy_swarm = self.swarms.get_enemy_swarm()
            enemy_ai = self.swarms.get_enemy_ai()
            
            self.gui.text(f"Player drones: {player_swarm.get_alive_count()}")
            self.gui.text(f"Enemy drones: {enemy_swarm.get_alive_count()}")
            self.gui.text(f"Player mode: {player_swarm.get_mode()}")
            self.gui.text(f"Enemy AI state: {enemy_ai.get_state()}")
            self.gui.text(f"Territory: {self.player_territory:.1f}%")
            
    @run_every_n_calls(10)
    def _calc_voronoi(self) -> None:
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
        
    def update(self) -> None:
        self._update_camera()
        self._update_bourndary()
        self._handle_input()
        
        if not self.GuiState.PAUSED:
            self.swarms.update(self.dt, self.GuiState)
        
        self._update_gui()
        self._calc_voronoi()
        if self.GuiState.SHOW_VORONOI:
            self.scene.mesh(self.voronoi.get_vertices(), per_vertex_color=self.voronoi.get_colors())