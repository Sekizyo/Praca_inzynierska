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
import taichi as ti
import time

class GUI():
    MAP_SIZE: float = 400.0
    
    def __init__(self, gui: Gui, window: TWindow, scene: SceneV2) -> None:
        self.gui = gui
        self.window = window
        self.scene = scene
        self.GuiState: GuiState = GuiState()
        
        self.dt: float = 0.15
        self.last_frame_time: float = time.perf_counter()
        self.drone_count: int = 1000
        self.player_territory: float = 50.0
        
    def load(self):
        yield "Initializing Swarms"
        self.swarms: Swarms = Swarms(self.scene, self.drone_count, self.MAP_SIZE)
        
        yield "Initializing Map"
        self.map = Map(self.scene, self.MAP_SIZE)
        
        yield "Initializing Voronoi"
        self.voronoi = VoronoiDiagram(boundary=self.MAP_SIZE)

        yield "Initializing Camera"
        self._init_camera()
        
        yield "Fetching Swarm references"
        self.player_swarm = self.swarms.get_player_swarm()
        self.enemy_swarm = self.swarms.get_enemy_swarm()
        self.enemy_ai = self.swarms.get_enemy_ai()
        
        yield "Finalizing"

    def reset(self):
        self.swarms.reset()
        self.voronoi.reset()
        self._init_camera()
        self.player_territory = 50.0
        
    def _init_camera(self) -> None:
        self.camera: Camera = Camera()
        self.camera.position(0, 0, 500)
        self.camera.lookat(0, 0, 0)
        self.camera.up(0, 1, 0)
        self.camera.fov(90)
        
    def _update_camera(self) -> None:
        self.camera.track_user_inputs(self.window, movement_speed=3, hold_key=RMB)
        self.scene.set_camera(self.camera)
        self.scene.point_light(pos=(0, 0, self.MAP_SIZE), color=(1, 1, 1))
        
    def _handle_input(self) -> None:
        self.window.get_event()
        if self.window.is_pressed("z"):
            self.player_swarm.update_mode(DroneModes.ATTACK)
        elif self.window.is_pressed("x"):
            self.player_swarm.update_mode(DroneModes.SPREAD)
        else:
            pass

        if self.window.is_pressed(LMB):
            mouse_pos = self.window.get_cursor_pos()
            x = (mouse_pos[0] - 0.5) * self.MAP_SIZE * 2.0
            y = (mouse_pos[1] - 0.5) * self.MAP_SIZE * 2.0
            self.swarms.set_player_target(x, y)

    def _update_gui(self) -> None:
        
        with self.gui.sub_window("Controls", 0.01, 0.01, 0.15, 0.4):
            if self.gui.button("Pause" if not self.GuiState.PAUSED else "Resume"):
                self.GuiState.PAUSED = not self.GuiState.PAUSED

            self.GuiState.SHOW_VORONOI = self.gui.checkbox("Show Voronoi", self.GuiState.SHOW_VORONOI)
            self.GuiState.SHOW_BOUNDARY = self.gui.checkbox("Show Boundary", self.GuiState.SHOW_BOUNDARY)
            self.GuiState.SHOW_GRID = self.gui.checkbox("Show Grid", self.GuiState.SHOW_GRID)
            
            if self.gui.button("Print Profile"):
                ti.profiler.print_kernel_profiler_info()
            
            if self.gui.button("Clear Profile"):
                ti.profiler.clear_kernel_profiler_info()
            
            # Calculate domination score
            player_count = self.player_swarm.get_alive_count()
            enemy_count = self.enemy_swarm.get_alive_count()
            total_drones = player_count + enemy_count
            
            if total_drones > 0:
                drone_ratio = player_count / total_drones
                territory_ratio = self.player_territory / 100.0
                domination = (drone_ratio * 0.7 + territory_ratio * 0.3)
            else:
                domination = 0.5
            
            self.gui.text(f"Player drones: {player_count}")
            self.gui.text(f"Enemy drones: {enemy_count}")
            self.gui.text(f"Player mode: {self.player_swarm.get_mode()}")
            self.gui.text(f"Enemy AI state: {self.enemy_ai.get_state()}")
            self.gui.text(f"Territory: {self.player_territory:.1f}%")
            self.gui.text(f"Win percentage: {domination*100:.1f}%")
            
            self.gui.text(f"Z - Attack mode")
            self.gui.text(f"X - Spread mode")
            self.gui.text(f"LMB - Set target position")
            self.gui.text(f"RMB - Move camera")
            
    @run_every_n_calls(20)
    def _calc_voronoi(self) -> None:
        self.voronoi.update(
            self.player_swarm.get_pos_field(), 
            self.player_swarm.N,
            self.player_swarm.health,
            self.enemy_swarm.get_pos_field(),
            self.enemy_swarm.N,
            self.enemy_swarm.health
        )
        
    def update(self) -> None:
        self.player_swarm.pull_stats()
        self.enemy_swarm.pull_stats()
        self.voronoi.pull_stats()
        
        self.player_territory = self.voronoi.get_territory_ratio()
        
        self._update_camera()
        self._handle_input()
        self._update_gui()
        
        if not self.GuiState.PAUSED:
            self._calc_voronoi()
            self.swarms.update_logic(self.dt, self.player_territory)
        self.swarms.update_draw(self.GuiState)
        
        if self.GuiState.SHOW_BOUNDARY:
            self.map.draw_boundary()
            
        if self.GuiState.SHOW_VORONOI:
            self.scene.mesh(self.voronoi.get_vertices(), per_vertex_color=self.voronoi.get_colors())