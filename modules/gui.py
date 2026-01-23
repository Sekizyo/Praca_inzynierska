from taichi.ui.scene import SceneV2
from taichi.ui.window import Window as TWindow
from taichi.ui.ui import Gui
from taichi.ui import Camera, LMB, RMB
from modules.map import Map
from modules.swarms import Swarms
from modules.constants import DroneModes, GameMode
from modules.voronoi import VoronoiDiagram
from modules.gui_utils import GuiState
from modules.utils import run_every_n_calls
import taichi as ti
import time

class GUI():
    MAP_SIZE: float = 400.0
    
    def __init__(self, gui: Gui, window: TWindow, scene: SceneV2, game_mode: GameMode, drone_count_player: int, drone_count_enemy: int, path_points: list[tuple[float, float]]) -> None:
        self.gui = gui
        self.window = window
        self.scene = scene
        self.GuiState: GuiState = GuiState()
        self.GameMode: GameMode = game_mode
        self.path_points = path_points
        
        self.dt: float = 0.15
        self.last_frame_time: float = time.perf_counter()
        self.drone_count_player: int = drone_count_player
        self.drone_count_enemy: int = drone_count_enemy
        self.stats_frame_counter: int = 0
        self.return_to_menu: bool = False
        self.victory: bool = False
        self.defeat: bool = False
        self.player_territory = 50.0
        
        self.start_time: float = 0.0
        self.stats_history = {
            "time": [],
            "player_count": [],
            "enemy_count": [],
            "territory": [],
            "damage_p": [], 
            "damage_e": [], 
            "kd_ratio": []  
        }
        
    def load(self):
        yield "Initializing Swarms"
        self.swarms: Swarms = Swarms(self.scene, self.drone_count_player, self.drone_count_enemy, self.MAP_SIZE)
        
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
        self.return_to_menu = False
        self.victory = False
        self.defeat = False
        self.GuiState.PAUSED = False
        
        self.start_time = time.time()
        self.stats_history = {"time": [], "player_count": [], "enemy_count": [], "territory": [], "damage_p": [], "damage_e": [], "kd_ratio": []}
        
    def _init_camera(self) -> None:
        self.camera: Camera = Camera()
        self.camera.position(0, 0, 500)
        self.camera.lookat(0, 0, 0)
        self.camera.up(0, 1, 0)
        self.camera.fov(90)
        
    def _update_camera(self) -> None:
        self.camera.track_user_inputs(self.window, movement_speed=3.0, hold_key=RMB)
        self.scene.set_camera(self.camera)
        self.scene.point_light(pos=(0, 0, self.MAP_SIZE), color=(1, 1, 1))
        
    def _handle_input(self) -> None:
        if self.GameMode == GameMode.RTS:
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
                
        self._update_camera()

    def _update_gui(self) -> None:
        with self.gui.sub_window("Controls", 0.01, 0.01, 0.15, 0.4):
            if self.gui.button("Main Menu"):
                self.return_to_menu = True
            
            if self.gui.button("Pause" if not self.GuiState.PAUSED else "Resume"):
                self.GuiState.PAUSED = not self.GuiState.PAUSED

            self.GuiState.SHOW_VORONOI = self.gui.checkbox("Show Voronoi", self.GuiState.SHOW_VORONOI)
            self.GuiState.SHOW_BOUNDARY = self.gui.checkbox("Show Boundary", self.GuiState.SHOW_BOUNDARY)
            self.GuiState.SHOW_GRID = self.gui.checkbox("Show Grid", self.GuiState.SHOW_GRID)
            
            self.stats_frame_counter += 1
            
            if self.stats_frame_counter % 30 == 0:
                self.player_swarm.pull_stats()
                self.enemy_swarm.pull_stats()
                self.voronoi.pull_stats()
                self.player_territory = self.voronoi.get_territory_ratio()
                self.stats_frame_counter = 0
                
                if not self.GuiState.PAUSED and not self.victory and not self.defeat:
                    current_t = time.time() - self.start_time
                    p_count = self.player_swarm.get_alive_count()
                    e_count = self.enemy_swarm.get_alive_count()
                    
                    p_dmg = self.player_swarm.total_damage[None]
                    e_dmg = self.enemy_swarm.total_damage[None]
                    p_deaths = self.player_swarm.death_count[None]
                    e_deaths = self.enemy_swarm.death_count[None]
                    
                    kd = e_deaths / max(1, p_deaths)
                    
                    self.stats_history["time"].append(current_t)
                    self.stats_history["player_count"].append(p_count)
                    self.stats_history["enemy_count"].append(e_count)
                    self.stats_history["territory"].append(self.player_territory)
                    self.stats_history["damage_p"].append(p_dmg)
                    self.stats_history["damage_e"].append(e_dmg)
                    self.stats_history["kd_ratio"].append(kd)

            player_count = self.player_swarm.get_alive_count()
            enemy_count = self.enemy_swarm.get_alive_count()
            total_drones = player_count + enemy_count
            
            if total_drones > 0:
                drone_ratio = player_count / total_drones
                territory_ratio = self.player_territory / 100.0
                domination = (drone_ratio * 0.7 + territory_ratio * 0.3)
            else:
                domination = 0.5
            
            if domination >= 0.95:
                self.victory = True
            
            if domination <= 0.05:
                self.defeat = True
            
            self.gui.text(f"Win percentage: {domination*100:.1f}%")
            self.gui.text(f"Player drones: {player_count}")
            self.gui.text(f"Enemy drones: {enemy_count}")
            self.gui.text(f"Player mode: {self.player_swarm.get_mode()}")
            self.gui.text(f"Enemy AI state: {self.enemy_ai.get_state()}")
            
            self.gui.text(f"Frame: {self.frame_time*1000:.2f}ms")
            self.gui.text(f"FPS: {1.0/(self.frame_time + 1e-5):.1f}")
            
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
        current_time = time.perf_counter()
        self.frame_time = current_time - self.last_frame_time
        self.last_frame_time = current_time

        if not self.GuiState.PAUSED:
            self._calc_voronoi()
            if self.GameMode == GameMode.MISSION_PLANNING:
                self.swarms.player_follow_path(self.path_points)
            self.swarms.update_logic(self.dt, self.player_territory)
            
            
        self._handle_input()
        self._update_gui()
        
        if self.GuiState.SHOW_BOUNDARY:
            self.map.draw_boundary()
            
        if self.GuiState.SHOW_VORONOI:
            self.scene.mesh(self.voronoi.get_vertices(), per_vertex_color=self.voronoi.get_colors())
        
        self.swarms.update_draw(self.GuiState)