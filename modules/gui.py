from taichi.ui.scene import SceneV2
from taichi.ui.window import Window as TWindow
from taichi.ui.ui import Gui
from taichi.ui import Camera, RMB
from modules.map import Map
from modules.swarms import Swarms
from modules.voronoi import VoronoiDiagram
from modules.gui_utils import GuiState, GamePresets
from modules.utils import run_every_n_calls
from modules.statistics import StatisticsLogger
import time

class GUI():
    def __init__(self, gui: Gui, window: TWindow, scene: SceneV2, gamePreset: GamePresets) -> None:
        self.gui = gui
        self.window = window
        self.scene = scene
        self.GuiState: GuiState = GuiState()
        self.gamePreset: GamePresets = gamePreset
        
        self.dt: float = 0.15
        self.last_frame_time: float = time.perf_counter()
        self.stats_frame_counter: int = 0
        self.total_frames: int = 0
        self.return_to_menu: bool = False
        self.victory: bool = False
        self.defeat: bool = False
        self.domination: float = 0.5
        self.player_territory = 50.0
        self.start_time: float = 0.0
        self.sim_elapsed_time: float = 0.0
        self.last_update_time: float = 0.0
        self.stats = StatisticsLogger()
        self.position_frame_counter: int = 0
        
    def load(self):
        yield "Initializing Swarms"
        self.swarms: Swarms = Swarms(self.scene, self.gamePreset)
        
        yield "Initializing Map"
        self.map = Map(self.scene, self.gamePreset)
        
        yield "Initializing Voronoi"
        self.voronoi = VoronoiDiagram(boundary=self.gamePreset.map_size)

        yield "Initializing Camera"
        self._init_camera()
        
        yield "Fetching Swarm references"
        self.attacking_swarm = self.swarms.get_attacking_swarm()
        self.defending_swarm = self.swarms.get_defending_swarm()
        
        yield "Finalizing"
        self.start_time = time.time()
        self.last_update_time = time.time()
        
    def _init_camera(self) -> None:
        self.camera: Camera = Camera()
        self.camera.position(0, 0, self.gamePreset.map_size * 1.5)
        self.camera.lookat(0, 0, 0)
        self.camera.up(0, 1, 0)
        self.camera.fov(90)
        self.camera.z_far(max(10000.0, self.gamePreset.map_size * 5.0))
        
    def _update_camera(self) -> None:
        self.camera.track_user_inputs(self.window, movement_speed=3.0, hold_key=RMB)
        self.scene.set_camera(self.camera)
        self.scene.point_light(pos=(0, 0, self.gamePreset.map_size), color=(1, 1, 1))
        
    def _update_gui(self) -> None:
        with self.gui.sub_window("Controls", 0.01, 0.01, 0.15, 0.4):
            if self.gui.button("Main Menu"):
                self.return_to_menu = True
            
            if self.gui.button("Pause" if not self.GuiState.PAUSED else "Resume"):
                self.GuiState.PAUSED = not self.GuiState.PAUSED

            self.GuiState.SHOW_VORONOI = self.gui.checkbox("Show Voronoi", self.GuiState.SHOW_VORONOI)
            self.GuiState.SHOW_BOUNDARY = self.gui.checkbox("Show Boundary", self.GuiState.SHOW_BOUNDARY)
            
            if not self.GuiState.PAUSED:
                self.total_frames += 1
                current_time = time.time()
                self.sim_elapsed_time += current_time - self.last_update_time
                self.last_update_time = current_time
            else:
                self.last_update_time = time.time()
                
            self.gui.text(f"Simulation Time: {self.sim_elapsed_time:.2f}s")
            self.stats_frame_counter += 1
            self.position_frame_counter += 1
            
            if self.stats_frame_counter >= self.gamePreset.stats_collection_frequency:
                self.attacking_swarm.get_stats()
                self.defending_swarm.get_stats()
                self.voronoi.pull_stats()
                self.player_territory = self.voronoi.get_territory_ratio()
                self.stats_frame_counter = 0
                
                if not self.GuiState.PAUSED and not self.victory and not self.defeat:
                    current_t = self.sim_elapsed_time
                    p_count = self.attacking_swarm.get_alive_count()
                    e_count = self.defending_swarm.get_alive_count()
                    
                    p_dmg = self.attacking_swarm.total_damage[None]
                    e_dmg = self.defending_swarm.total_damage[None]
                    p_deaths = self.attacking_swarm.death_count[None]
                    e_deaths = self.defending_swarm.death_count[None]
                    
                    kd = e_deaths / max(1, p_deaths)
                    
                    self.stats.record(self.total_frames, current_t, p_count, e_count, 
                                      self.player_territory, p_dmg, e_dmg, p_deaths, e_deaths, kd)

            if self.position_frame_counter >= self.gamePreset.position_collection_frequency:
                self.position_frame_counter = 0
                
                if not self.GuiState.PAUSED and not self.victory and not self.defeat:
                    p_pos = self.attacking_swarm.pos.to_numpy()
                    p_active = self.attacking_swarm.active.to_numpy().flatten()
                    
                    e_pos = self.defending_swarm.pos.to_numpy()
                    e_active = self.defending_swarm.active.to_numpy().flatten()
                    
                    alive_p_pos = p_pos[p_active == 1]
                    alive_e_pos = e_pos[e_active == 1]
                    
                    self.stats.record_positions(self.total_frames, alive_p_pos, alive_e_pos)

            attacking_count = self.attacking_swarm.get_alive_count()
            defending_count = self.defending_swarm.get_alive_count()
            total_drones = attacking_count + defending_count

            if total_drones > 0:
                drone_ratio = defending_count / total_drones
                territory_ratio = self.player_territory / 100.0
                self.domination = (drone_ratio * 0.8 + territory_ratio * 0.2)
            else:
                self.domination = 0.5
            
            if self.domination >= 0.95:
                self.victory = True
            
            if self.domination <= 0.05:
                self.defeat = True
            
            self.gui.text(f"Defending swarm win: {self.domination*100:.1f}%")
            self.gui.text(f"Attacking drones: {attacking_count}")
            self.gui.text(f"Defending drones: {defending_count}")
            self.gui.text(f"Attacking mode: {self.attacking_swarm.get_mode()}")
            self.gui.text(f"Defending mode: {self.defending_swarm.get_mode()}")
            
            self.gui.text(f"FPS: {1.0/(self.frame_time + 1e-5):.1f}")
            self.gui.text(f"Frame: {self.frame_time*1000:.2f}ms")
            
    @run_every_n_calls(20)
    def _calc_voronoi(self) -> None:
        self.voronoi.update(
            self.attacking_swarm.get_pos_field(), 
            self.attacking_swarm.N,
            self.attacking_swarm.health,
            self.defending_swarm.get_pos_field(),
            self.defending_swarm.N,
            self.defending_swarm.health
        )
        
    def update(self) -> None:
        current_time = time.perf_counter()
        self.frame_time = current_time - self.last_frame_time
        self.last_frame_time = current_time

        if not self.GuiState.PAUSED:
            self._calc_voronoi()
            self.swarms.update_logic(self.dt, self.domination, self.map.obstacle_pos, self.map.obstacle_radius, self.map.obstacle_count)
            
        if self.GuiState.SHOW_BOUNDARY: self.map.draw_boundary()
        self.map.draw_obstacles()
            
        if self.GuiState.SHOW_VORONOI: self.scene.mesh(self.voronoi.get_vertices(), per_vertex_color=self.voronoi.get_colors())
        
        self._update_camera()
        self._update_gui()
        
        self.swarms.update_draw()