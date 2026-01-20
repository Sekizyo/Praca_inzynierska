import taichi as ti
import threading
from typing import Optional
from taichi.ui.canvas import SceneV2
from taichi.ui.window import Window as TWindow
from taichi.ui import LMB, Canvas
from modules.gui import GUI
from modules.colors import *
from modules.constants import GameMode

class Window():
    MAP_SIZE: float = 250.0
    DRONE_PRESETS: list[int] = [500, 1000, 2000, 4000, 8000]
    STATE_MENU: int = 0
    STATE_LOADING: int = 1
    STATE_GAME: int = 2
    STATE_VICTORY: int = 3
    STATE_DEFEAT: int = 4
    STATE_PLANNING: int = 5
    
    def __init__(self, title="Drone Voronoi Sim", size=(1920, 1000)) -> None:
        ti.init(arch=ti.vulkan, default_fp=ti.f32, default_ip=ti.i32, offline_cache=True, kernel_profiler=False, advanced_optimization=True, fast_math=True)        
        self.window: TWindow = TWindow(title, size, pos=(0,30), show_window=True, vsync=False)
        self.canvas: Canvas = self.window.get_canvas()
        self.scene: SceneV2 = self.window.get_scene()
        self.gui: Optional[GUI] = None
        self.loader = None
        
        
        self.state: int = self.STATE_MENU
        self.loading_text: str = 'Starting'
        self.loading_frames: int = 0
        self.drone_count: int = 0
        self.selected_preset: int = 1
        self.attacking_drone_count: int = self.DRONE_PRESETS[1]
        self.defending_drone_count: int = self.DRONE_PRESETS[1]

    def _render_menu(self) -> None:
        self.canvas.set_background_color(MENU_BACKGROUND_COLOR)
        gui = self.window.get_gui()

        with gui.sub_window('Drone Voronoi Sim', 0.3, 0.2, 0.4, 0.6):
            gui.text('Welcome to Drone Voronoi Simulator', color=TEXT_COLOR_WHITE)
            gui.text('')
            gui.text('Select drone count per team:', color=TEXT_COLOR_GRAY)
            gui.text('')

            for i, preset in enumerate(self.DRONE_PRESETS):
                label = f'> {preset} drones <' if i == self.selected_preset else f'  {preset} drones  '
                if gui.button(label):
                    self.selected_preset = i
                    self.attacking_drone_count = preset
                    self.defending_drone_count = preset

            gui.text('')
            gui.text(f'Selected: {self.attacking_drone_count} drones per team', color=TEXT_COLOR_GREEN)
            gui.text(f'Total drones: {self.attacking_drone_count + self.defending_drone_count}', color=TEXT_COLOR_GREEN)
            gui.text('')

            if gui.button('Real-Time Mode'):
                self._start_game(GameMode.RTS)
                
            if gui.button('Pre-Planned Mode'):
                self.state = self.STATE_PLANNING
                
            gui.text('')
            gui.text('Game Rules:', color=TEXT_COLOR_DARK_GRAY)
            gui.text('1. Control your drones to dominate the map.', color=TEXT_COLOR_LIGHT_GRAY)
            gui.text('2. Use LMB to set target positions.', color=TEXT_COLOR_LIGHT_GRAY)
            gui.text('3. Use Z for attack mode and X for spread mode.', color=TEXT_COLOR_LIGHT_GRAY)
            gui.text('4. Achieve victory by eliminating all enemy drones.', color=TEXT_COLOR_LIGHT_GRAY)
            gui.text('')

            gui.text('Controls:', color=TEXT_COLOR_DARK_GRAY)
            gui.text('LMB - Set target position', color=TEXT_COLOR_LIGHT_GRAY)
            gui.text('RMB - Move camera', color=TEXT_COLOR_LIGHT_GRAY)
            gui.text('Z - Attack mode', color=TEXT_COLOR_LIGHT_GRAY)
            gui.text('X - Spread mode', color=TEXT_COLOR_LIGHT_GRAY)
            
    def _render_planning_menu(self) -> None:
            self.canvas.set_background_color(MENU_BACKGROUND_COLOR)
            gui = self.window.get_gui()

            if not hasattr(self, 'planning_border_field'):
                self.planning_border_field = ti.Vector.field(2, dtype=ti.f32, shape=8)
                self.planning_path_field = ti.Vector.field(2, dtype=ti.f32, shape=2000)
                self.planning_start_pos = ti.Vector.field(2, dtype=ti.f32, shape=2)
                self.planning_start_col = ti.Vector.field(3, dtype=ti.f32, shape=2)
                
                self.path_points: list[tuple[float, float]] = []

            with gui.sub_window('Mission Control', 0.05, 0.2, 0.3, 0.6):
                if gui.button('Return to Main Menu'):
                    self._back_to_main_menu()
                gui.text('')
                gui.text('Mission Planning', color=TEXT_COLOR_WHITE)
                gui.text('')
                
                gui.text('Attacking Team:', color=TEXT_COLOR_GRAY)
                self.attacking_drone_count = gui.slider_int('Attacking', self.attacking_drone_count, self.DRONE_PRESETS[0], self.DRONE_PRESETS[-1])
                gui.text(f'Count: {self.attacking_drone_count}', color=TEXT_COLOR_GREEN)
                gui.text('')
                
                gui.text('Defending Team:', color=TEXT_COLOR_GRAY)
                self.defending_drone_count = gui.slider_int('Defending', self.defending_drone_count, self.DRONE_PRESETS[0], self.DRONE_PRESETS[-1])
                gui.text(f'Count: {self.defending_drone_count}', color=TEXT_COLOR_GREEN)
                gui.text('')

                gui.text('Path Planning:', color=TEXT_COLOR_LIGHT_GRAY)
                gui.text('Green: Player Start', color=TEXT_COLOR_GREEN)
                gui.text('Red: Enemy Start', color=TEXT_DEFEAT_COLOR)

                if gui.button('Clear Path'):
                    self.path_points = []
                    self.planning_path_field.fill(0)
                    

                gui.text('')
                if gui.button('Start Game'):
                    self._start_game(GameMode.MISSION_PLANNING)

            window_shape = self.window.get_window_shape()
            aspect_ratio = window_shape[0] / window_shape[1]
            
            sq_h = 0.6
            sq_w = sq_h / aspect_ratio
            sq_x = 0.45 
            
            min_x, min_y = sq_x, 0.2
            max_x, max_y = sq_x + sq_w, 0.2 + sq_h

            self.planning_border_field[0] = [min_x, min_y]; self.planning_border_field[1] = [max_x, min_y]
            self.planning_border_field[2] = [max_x, min_y]; self.planning_border_field[3] = [max_x, max_y]
            self.planning_border_field[4] = [max_x, max_y]; self.planning_border_field[5] = [min_x, max_y]
            self.planning_border_field[6] = [min_x, max_y]; self.planning_border_field[7] = [min_x, min_y]

            self.canvas.lines(self.planning_border_field, width=0.005, color=(1, 1, 1))

            p_x = min_x + (0.2 * sq_w)
            p_y = min_y + (0.5 * sq_h)
            e_x = min_x + (0.8 * sq_w)
            e_y = min_y + (0.5 * sq_h)

            self.planning_start_pos[0] = [p_x, p_y] # Gracz
            self.planning_start_pos[1] = [e_x, e_y] # Wróg

            self.planning_start_col[0] = [0.2, 0.8, 0.2] # Zielony (Gracz)
            self.planning_start_col[1] = [0.8, 0.2, 0.2] # Czerwony (Wróg)

            self.canvas.circles(self.planning_start_pos, radius=0.015, per_vertex_color=self.planning_start_col)

            if self.window.is_pressed(LMB):
                curr_mouse = self.window.get_cursor_pos()
                if min_x <= curr_mouse[0] <= max_x and min_y <= curr_mouse[1] <= max_y:
                    should_add = True
                    if len(self.path_points) > 0:
                        last_pt = self.path_points[-1]
                        dist_sq = (curr_mouse[0] - last_pt[0])**2 + (curr_mouse[1] - last_pt[1])**2
                        if dist_sq < 0.00005: 
                            should_add = False
                    if should_add:
                        self.path_points.append(curr_mouse)
            # 6. Rysowanie ścieżki
            path_len = len(self.path_points)
            if path_len > 1:
                max_segments = 1000
                segments_to_draw = min(path_len - 1, max_segments)
                for i in range(segments_to_draw):
                    p_curr = self.path_points[i]
                    p_next = self.path_points[i+1]
                    self.planning_path_field[2*i] = [p_curr[0], p_curr[1]]
                    self.planning_path_field[2*i+1] = [p_next[0], p_next[1]]
                
                self.canvas.lines(self.planning_path_field, width=0.003, color=(0, 1, 0))
                
    def _back_to_main_menu(self) -> None:
        self.gui.GuiState.PAUSED = True
        self.loader = None
        self.state = self.STATE_MENU
        self.loading_frames = 0

    def _start_game(self, game_mode: GameMode) -> None:
        self.state = self.STATE_LOADING
        self.canvas.set_background_color((0, 0, 0))
        
        world_path_points = []
        if self.path_points:
            window_shape = self.window.get_window_shape()
            aspect_ratio = window_shape[0] / window_shape[1]
            sq_h = 0.6
            sq_w = sq_h / aspect_ratio
            sq_x = 0.45 
            min_x, min_y = sq_x, 0.2
            max_x, max_y = sq_x + sq_w, 0.2 + sq_h
            
            for pt in self.path_points:
                norm_x = (pt[0] - min_x) / (max_x - min_x)
                norm_y = (pt[1] - min_y) / (max_y - min_y)
                
                
                world_x = (norm_x - 0.5) * 2 * self.MAP_SIZE
                world_y = (norm_y - 0.5) * 2 * self.MAP_SIZE
                
                world_path_points.append((world_x, world_y))

        # Przekazujemy przeliczone punkty
        self.gui = GUI(self.window.get_gui(), self.window, self.scene, game_mode, self.attacking_drone_count, self.defending_drone_count, world_path_points)
        self.loader = self.gui.load()
        threading.Thread(target=self._run_loader, daemon=True).start()

    def _render_loading(self) -> None:
        self.canvas.set_background_color((0, 0, 0))
        with self.window.get_gui().sub_window('Loading', 0.4, 0.45, 0.2, 0.1):
            self.window.get_gui().text(f"{self.loading_text}{'.' * ((self.loading_frames // 100) % 4)}", color=TEXT_COLOR_WHITE)
    
    def _run_loader(self) -> None:
        for text in self.loader:
            self.loading_text = text
        self.state = self.STATE_GAME

    def _render_victory(self) -> None:
        self.canvas.set_background_color(MENU_BACKGROUND_VICTORY_COLOR)
        gui = self.window.get_gui()
        
        with gui.sub_window('Victory', 0.3, 0.3, 0.4, 0.4):
            gui.text('VICTORY!', color=TEXT_VICTORY_COLOR)
            gui.text('')
            gui.text('You have achieved total domination!', color=TEXT_COLOR_WHITE)
            gui.text('')
            
            if gui.button('Return to Main Menu'):
                self._back_to_main_menu()

    def _render_defeat(self) -> None:
        self.canvas.set_background_color(MENU_BACKGROUND_DEFEAT_COLOR)
        gui = self.window.get_gui()
        
        with gui.sub_window('Defeat', 0.3, 0.3, 0.4, 0.4):
            gui.text('DEFEAT', color=TEXT_DEFEAT_COLOR)
            gui.text('')
            gui.text('Your forces have been eliminated!', color=TEXT_COLOR_WHITE)
            gui.text('')
            
            if gui.button('Return to Main Menu'):
                self._back_to_main_menu()
                
    def run(self) -> None:
        while self.window.running:
            if self.state == self.STATE_MENU:
                self._render_menu()
                self.window.show()
            elif self.state == self.STATE_LOADING:
                self._render_loading()
                self.window.show()
                self.loading_frames += 1
            elif self.state == self.STATE_PLANNING:
                self._render_planning_menu()
                self.window.show()
                self.loading_frames += 1
            elif self.state == self.STATE_VICTORY:
                self._render_victory()
                self.window.show()
            elif self.state == self.STATE_DEFEAT:
                self._render_defeat()
                self.window.show()
            else:
                if self.gui.return_to_menu:
                    self.gui.return_to_menu = False
                    self.loader = None
                    self.state = self.STATE_MENU
                    self.loading_frames = 0
                    continue
                if self.gui.victory:
                    self.state = self.STATE_VICTORY
                    continue
                if self.gui.defeat:
                    self.state = self.STATE_DEFEAT
                    continue
                self.gui.update()
                self.canvas.scene(self.scene)
                self.window.show()
