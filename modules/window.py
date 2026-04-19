import taichi as ti
import threading
import multiprocessing 
from taichi.ui.canvas import SceneV2
from taichi.ui.window import Window as TWindow
from taichi.ui import LMB, Canvas
from modules.gui import GUI
from modules.colors import *
from modules.constants import GameMode
import matplotlib.pyplot as plt
from modules.gui_utils import GamePresets
from modules.loader import FileManager

def run_plot_process(history: dict) -> None:
    try:
        plt.style.use('dark_background')
        
        fig, axs = plt.subplots(2, 2, figsize=(14, 10))
        if fig is None: return None
        fig.canvas.manager.set_window_title('Mission Analysis')
        
        axs[0, 0].plot(history['time'], history['player_count'], label='Player', color='green')
        axs[0, 0].plot(history['time'], history['enemy_count'], label='Enemy', color='red')
        axs[0, 0].set_title('Drone Population')
        axs[0, 0].set_ylabel('Count')
        axs[0, 0].legend()
        axs[0, 0].grid(True, alpha=0.3)
        
        axs[0, 1].plot(history['time'], history['territory'], label='Player Control', color='cyan')
        axs[0, 1].fill_between(history['time'], history['territory'], alpha=0.2, color='cyan')
        axs[0, 1].axhline(y=50, color='gray', linestyle='--', alpha=0.5)
        axs[0, 1].set_title('Territory Control (%)')
        axs[0, 1].set_ylim(0, 100)
        axs[0, 1].grid(True, alpha=0.3)
        
        axs[1, 0].plot(history['time'], history['damage_p'], label='Player Dmg', color='lightgreen')
        axs[1, 0].plot(history['time'], history['damage_e'], label='Enemy Dmg', color='salmon')
        axs[1, 0].set_title('Total Damage Dealt (Cumulative)')
        axs[1, 0].set_ylabel('Damage')
        axs[1, 0].legend()
        axs[1, 0].grid(True, alpha=0.3)
        
        if 'kd_ratio' in history:
            axs[1, 1].plot(history['time'], history['kd_ratio'], label='Player K/D', color='gold')
            axs[1, 1].axhline(y=1.0, color='white', linestyle='--', label='Even (1.0)')
            axs[1, 1].set_title('Kill / Death Ratio')
            axs[1, 1].set_xlabel('Time (s)')
            axs[1, 1].legend()
            axs[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    except Exception as e:
        raise 
    
class Window():
    STATE_LOADING: int = 1
    STATE_GAME: int = 2
    STATE_VICTORY: int = 3
    STATE_DEFEAT: int = 4
    STATE_PLANNING: int = 5
    
    def __init__(self, title="Drone Sim", size=(1920, 1000)) -> None:
        ti.init(arch=ti.vulkan, default_fp=ti.f32, default_ip=ti.i32, offline_cache=True, offline_cache_file_path="ticache", offline_cache_cleaning_policy="lru", kernel_profiler=False, fast_math=True, debug=False)        
        self.window: TWindow = TWindow(title, size, pos=(0,30), show_window=True, vsync=False)
        self.canvas: Canvas = self.window.get_canvas()
        self.scene: SceneV2 = self.window.get_scene()
        self.gui: GUI | None = None
        self.loader = None
        self.gamePreset: GamePresets = GamePresets()
        
        self.state: int = self.STATE_PLANNING
        self.loading_text: str = 'Starting'
        self.loading_frames: int = 0

    def _reset_planning_fields(self) -> None:
        self.planning_path_field.fill(0)
        self.gamePreset: GamePresets = GamePresets()
        
    def _render_planning_menu(self) -> None:
            self.canvas.set_background_color(MENU_BACKGROUND_COLOR)
            gui = self.window.get_gui()

            if not hasattr(self, 'planning_border_field'):
                self.planning_border_field = ti.Vector.field(2, dtype=ti.f32, shape=8)
                self.planning_path_field = ti.Vector.field(2, dtype=ti.f32, shape=2000)
                self.planning_start_pos = ti.Vector.field(2, dtype=ti.f32, shape=2)
                self.planning_start_col = ti.Vector.field(3, dtype=ti.f32, shape=2)
                
            with gui.sub_window('Mission Planning', 0.05, 0.1, 0.3, 0.8):
                gui.text('')
                gui.text('Mission Planning', color=TEXT_COLOR_WHITE)
                gui.text('Draw a path for drones to follow on the right panel.', color=TEXT_COLOR_LIGHT_GRAY)
                
                gui.text('')
                gui.text('Critical parameters:', color=TEXT_COLOR_DARK_GRAY)
                self.gamePreset.map_size = gui.slider_int('Map size', self.gamePreset.map_size, 50, 1000)
                self.gamePreset.attacking_drone_count = gui.slider_int('Attacking Team', self.gamePreset.attacking_drone_count, 1, 8000)
                self.gamePreset.defending_drone_count = gui.slider_int('Defending Team', self.gamePreset.defending_drone_count, 1, 8000)

                gui.text('')
                gui.text('AI parameters:', color=TEXT_COLOR_DARK_GRAY)
                self.gamePreset.ai_engage_distance = gui.slider_int('Engage Distance', self.gamePreset.ai_engage_distance, 0, self.gamePreset.map_size)
                self.gamePreset.ai_agression_threshold = gui.slider_float('Aggression', self.gamePreset.ai_agression_threshold, 0, 1.0)
                self.gamePreset.ai_evaluate_state = gui.slider_int('Evaluate State', self.gamePreset.ai_evaluate_state, 1, 50)
                self.gamePreset.ai_execute_state = gui.slider_int('Execute State', self.gamePreset.ai_execute_state, 1, 50)
                
                gui.text('')
                gui.text('Boids parameters:', color=TEXT_COLOR_DARK_GRAY)
                self.gamePreset.boids_attack_separation = gui.slider_float('Attack Separation', self.gamePreset.boids_attack_separation, 1, 10)
                self.gamePreset.boids_attack_alignment = gui.slider_float('Attack Alignment', self.gamePreset.boids_attack_alignment, 1, 10)
                self.gamePreset.boids_attack_cohesion = gui.slider_float('Attack Cohesion', self.gamePreset.boids_attack_cohesion, 1, 10)
                self.gamePreset.boids_attack_target = gui.slider_float('Attack Target', self.gamePreset.boids_attack_target, 1, 10)
                
                self.gamePreset.boids_spread_separation = gui.slider_float('Spread Separation', self.gamePreset.boids_spread_separation, 1, 10)
                self.gamePreset.boids_spread_alignment = gui.slider_float('Spread Alignment', self.gamePreset.boids_spread_alignment, 1, 10)
                self.gamePreset.boids_spread_cohesion = gui.slider_float('Spread Cohesion', self.gamePreset.boids_spread_cohesion, 1, 10)
                self.gamePreset.boids_spread_target = gui.slider_float('Spread Target', self.gamePreset.boids_spread_target, 1, 10)
                
                gui.text('')
                gui.text('Drone parameters:', color=TEXT_COLOR_DARK_GRAY)
                self.gamePreset.drone_max_speed = gui.slider_int('Max Speed', self.gamePreset.drone_max_speed, 1, 100)
                self.gamePreset.drone_shooting_range = gui.slider_int('Shooting Range', self.gamePreset.drone_shooting_range, 0, self.gamePreset.map_size)
                self.gamePreset.drone_shooting_cooldown = gui.slider_float('Shooting Cooldown', self.gamePreset.drone_shooting_cooldown, 0, 100)
                self.gamePreset.drone_max_health = gui.slider_int('Max Health', self.gamePreset.drone_max_health, 1, 500)
                self.gamePreset.drone_perception_radius = gui.slider_int('Perception Radius', self.gamePreset.drone_perception_radius, 0, 360)
                self.gamePreset.drone_hit_radius = gui.slider_int('Hit Radius', self.gamePreset.drone_hit_radius, 1, 5)
                
                gui.text('')
                gui.text('Projectiles parameters:', color=TEXT_COLOR_DARK_GRAY)
                self.gamePreset.projectile_damage = gui.slider_int('Damage', self.gamePreset.projectile_damage, 1, self.gamePreset.drone_max_health)
                self.gamePreset.projectile_speed = gui.slider_int('Speed', self.gamePreset.projectile_speed, 1, 100)
                self.gamePreset.projectile_radius = gui.slider_int('Radius', self.gamePreset.projectile_radius, 1, 5)
                self.gamePreset.projectile_max_lifetime = gui.slider_float('Max Lifetime', self.gamePreset.projectile_max_lifetime, 0.5, 10)
                
                gui.text('')
                gui.text('Path Planning:', color=TEXT_COLOR_LIGHT_GRAY)
                gui.text('Green: Attacking Start', color=TEXT_COLOR_GREEN)
                gui.text('Red: Defending Start', color=TEXT_DEFEAT_COLOR)

                if gui.button('Reset'): self._reset_planning_fields()
                if gui.button('Save Scenario'): gui.text("Saved successfully.") if not FileManager().create_config(self.gamePreset.generate_config_dict()) else gui.text('Failed to save scenario.', color=TEXT_DEFEAT_COLOR)
                if gui.button('Load Scenario'): self.gamePreset.load_config(FileManager().load_config())
                    
                gui.text('')
                if self.gamePreset.attacking_path == []:
                    gui.text('Please draw a attack path before starting the game.', color=TEXT_DEFEAT_COLOR)
                if self.gamePreset.ai_path == []:
                    gui.text('Please draw a ai path before starting the game.', color=TEXT_DEFEAT_COLOR)
                
                if gui.button('Start Game'): self._start_game()

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
            p_y = min_y + (0.1 * sq_h)
            e_x = min_x + (0.8 * sq_w)
            e_y = min_y + (0.9 * sq_h)

            self.planning_start_pos[0] = [p_x, p_y] # Gracz
            self.planning_start_pos[1] = [e_x, e_y] # Wróg

            self.planning_start_col[0] = [0.2, 0.8, 0.2] # Zielony (Gracz)
            self.planning_start_col[1] = [0.8, 0.2, 0.2] # Czerwony (Wróg)

            self.canvas.circles(self.planning_start_pos, radius=0.015, per_vertex_color=self.planning_start_col)

            if self.window.is_pressed(LMB):
                curr_mouse = self.window.get_cursor_pos()
                if min_x <= curr_mouse[0] <= max_x and min_y <= curr_mouse[1] <= max_y:
                    should_add = True
                    if len(self.gamePreset.attacking_path) > 0:
                        last_pt = self.gamePreset.attacking_path[-1]
                        dist_sq = (curr_mouse[0] - last_pt[0])**2 + (curr_mouse[1] - last_pt[1])**2
                        if dist_sq < 0.001: 
                            should_add = False
                    if should_add:
                        self.gamePreset.attacking_path.append(curr_mouse)
                        
            path_len = len(self.gamePreset.attacking_path)
            if path_len > 1:
                max_segments = 1000
                segments_to_draw = min(path_len - 1, max_segments)
                for i in range(segments_to_draw):
                    p_curr = self.gamePreset.attacking_path[i]
                    p_next = self.gamePreset.attacking_path[i+1]
                    self.planning_path_field[2*i] = [p_curr[0], p_curr[1]]
                    self.planning_path_field[2*i+1] = [p_next[0], p_next[1]]
                
                self.canvas.lines(self.planning_path_field, width=0.003, color=(0, 1, 0))
                
    def _back_to_main_menu(self) -> None:
        if self.gui:
            self.gui.GuiState.PAUSED = True
        self.loader = None
        self.state = self.STATE_PLANNING
        self.loading_frames = 0

    def _start_game(self) -> None:
        self.state = self.STATE_LOADING
        self.canvas.set_background_color((0, 0, 0))
        
        self.gui = GUI(self.window.get_gui(), self.window, self.scene, self.gamePreset)
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

    def _show_mission_analysis(self) -> None:
        if not self.gui or not hasattr(self.gui, 'stats_history'):
            return
            
        history = self.gui.stats_history
        if not history['time']:
            return

        p = multiprocessing.Process(target=run_plot_process, args=(history,))
        p.start()

    def _render_victory(self) -> None:
        self.canvas.set_background_color(MENU_BACKGROUND_VICTORY_COLOR)
        gui = self.window.get_gui()
        
        with gui.sub_window('Victory', 0.3, 0.3, 0.4, 0.4):
            gui.text('VICTORY!', color=TEXT_VICTORY_COLOR)
            gui.text('')
            gui.text('You have achieved total domination!', color=TEXT_COLOR_WHITE)
            gui.text('')
        
            if gui.button('Show Mission Analysis'):
                self._show_mission_analysis()
            
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
            
            if gui.button('Show Mission Analysis'):
                self._show_mission_analysis()
        
            if gui.button('Return to Main Menu'):
                self._back_to_main_menu()
                
    def run(self) -> None:
        while self.window.running:
            if self.state == self.STATE_LOADING:
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
                self.gui.update()
                self.canvas.scene(self.scene)
                self.window.show()