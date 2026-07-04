import taichi as ti
import threading
import multiprocessing 
import random
import math
import os
import csv
from datetime import datetime
from taichi.ui.canvas import SceneV2
from taichi.ui.window import Window as TWindow
from taichi.ui import LMB, RMB, Canvas
from modules.gui import GUI
from modules.colors import *
from modules.gui_utils import GamePresets
from modules.loader import FileManager
from modules.constants import DroneModes

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
        
        self.multirun_active: bool = False
        self.multirun_total_runs: int = 1
        self.multirun_current_run: int = 0
        self.multirun_results: list = []
        self.multirun_path_mode: int = 0
        self.multirun_paths: list = []
        self.multirun_random_points: int = 3

    def _reset_planning_fields(self) -> None:
        self.planning_path_field.fill(0)
        self.planning_ai_path_field.fill(0)
        self.gamePreset: GamePresets = GamePresets()
        
    def _render_common_planning_parameters(self, gui) -> None:
        gui.text('')
        gui.text('Execution Mode:', color=TEXT_COLOR_DARK_GRAY)
        
        self.multirun_total_runs = gui.slider_int('Number of simulation runs', self.multirun_total_runs, 1, 100)
        
        gui.text('Attacking Path Strategy:', color=TEXT_COLOR_DARK_GRAY)
        path_modes = ["Manual", "Line", "Circle", "Random"]
        
        prev_mode = self.multirun_path_mode
        prev_runs = self.multirun_total_runs
        prev_rand_pts = getattr(self, 'multirun_random_points', 3)

        self.multirun_path_mode = gui.slider_int(f'Selected: {path_modes[self.multirun_path_mode]}', self.multirun_path_mode, 0, 3)
        
        if self.multirun_path_mode == 3:
            self.multirun_random_points = gui.slider_int('Random Points', getattr(self, 'multirun_random_points', 3), 1, 20)
        
        if self.multirun_path_mode != prev_mode or self.multirun_total_runs != prev_runs or (self.multirun_path_mode == 3 and self.multirun_random_points != prev_rand_pts) or (self.multirun_path_mode != 0 and len(self.gamePreset.attacking_path) == 0):
            if self.multirun_path_mode == 0:
                self.gamePreset.attacking_path = []
                self.planning_path_field.fill(0)
                self.multirun_paths = []
            else:
                self._generate_multirun_path()

        if self.multirun_path_mode == 3:
            if gui.button('Regenerate Random Path'):
                self._generate_multirun_path()
                
        gui.text('')
        gui.text('Critical parameters:', color=TEXT_COLOR_DARK_GRAY)
        self.gamePreset.map_size = gui.slider_int('Map size', self.gamePreset.map_size, 50, 1000)
        self.gamePreset.attacking_drone_count = gui.slider_int('Attacking Team', self.gamePreset.attacking_drone_count, 1, 8000)
        self.gamePreset.defending_drone_count = gui.slider_int('Defending Team', self.gamePreset.defending_drone_count, 1, 8000)

        gui.text('')
        gui.text('Defending AI parameters:', color=TEXT_COLOR_DARK_GRAY)
        self.gamePreset.ai_engage_distance = gui.slider_int('Engage Distance', self.gamePreset.ai_engage_distance, 0, self.gamePreset.map_size)
        self.gamePreset.ai_agression_threshold = gui.slider_float('Aggression', self.gamePreset.ai_agression_threshold, 0, 1.0)
        self.gamePreset.ai_evaluate_state = gui.slider_int('Evaluate State', self.gamePreset.ai_evaluate_state, 1, 50)
        self.gamePreset.ai_execute_state = gui.slider_int('Execute State', self.gamePreset.ai_execute_state, 1, 50)
        self.gamePreset.fog_of_war = gui.checkbox('Fog of War', self.gamePreset.fog_of_war)
        if self.gamePreset.fog_of_war:
            self.gamePreset.fog_of_war_radius = gui.slider_int('Fog of War Radius', self.gamePreset.fog_of_war_radius, 0, 10)
        
        gui.text('')
        gui.text('Boids parameters:', color=TEXT_COLOR_DARK_GRAY)
        self.gamePreset.boids_attack_separation = gui.slider_float('Attack Separation', self.gamePreset.boids_attack_separation, 1, 10)
        self.gamePreset.boids_attack_alignment = gui.slider_float('Attack Alignment', self.gamePreset.boids_attack_alignment, 1, 10)
        self.gamePreset.boids_attack_cohesion = gui.slider_float('Attack Cohesion', self.gamePreset.boids_attack_cohesion, 1, 10)
        self.gamePreset.boids_attack_target = gui.slider_float('Attack Target', self.gamePreset.boids_attack_target, 1, 10)
        
        gui.text('')
        self.gamePreset.boids_spread_separation = gui.slider_float('Spread Separation', self.gamePreset.boids_spread_separation, 1, 10)
        self.gamePreset.boids_spread_alignment = gui.slider_float('Spread Alignment', self.gamePreset.boids_spread_alignment, 1, 10)
        self.gamePreset.boids_spread_cohesion = gui.slider_float('Spread Cohesion', self.gamePreset.boids_spread_cohesion, 1, 10)
        self.gamePreset.boids_spread_target = gui.slider_float('Spread Target', self.gamePreset.boids_spread_target, 1, 10)
        
        gui.text('')
        self.gamePreset.boids_patrol_separation = gui.slider_float('Patrol Separation', self.gamePreset.boids_patrol_separation, 1, 10)
        self.gamePreset.boids_patrol_alignment = gui.slider_float('Patrol Alignment', self.gamePreset.boids_patrol_alignment, 1, 10)
        self.gamePreset.boids_patrol_cohesion = gui.slider_float('Patrol Cohesion', self.gamePreset.boids_patrol_cohesion, 1, 10)
        self.gamePreset.boids_patrol_target = gui.slider_float('Patrol Target', self.gamePreset.boids_patrol_target, 1, 10)
        
        gui.text('')
        gui.text('Drone parameters:', color=TEXT_COLOR_DARK_GRAY)
        self.gamePreset.drone_max_speed = gui.slider_int('Max Speed', self.gamePreset.drone_max_speed, 1, 100)
        self.gamePreset.drone_shooting_range = gui.slider_int('Shooting Range', self.gamePreset.drone_shooting_range, 0, self.gamePreset.map_size)
        self.gamePreset.drone_shooting_cooldown = gui.slider_float('Shooting Cooldown', self.gamePreset.drone_shooting_cooldown, 0, 100)
        self.gamePreset.drone_max_health = gui.slider_int('Max Health', self.gamePreset.drone_max_health, 1, 500)
        self.gamePreset.drone_perception_radius = gui.slider_int('Perception Radius', self.gamePreset.drone_perception_radius, 0, 360)
        self.gamePreset.drone_shooting_perception_radius = gui.slider_float('Shooting Perception Radius', self.gamePreset.drone_shooting_perception_radius, 0, 1)
        self.gamePreset.drone_hit_radius = gui.slider_int('Hit Radius', self.gamePreset.drone_hit_radius, 1, 5)
        
        gui.text('')
        gui.text('Statistics parameters:', color=TEXT_COLOR_DARK_GRAY)
        self.gamePreset.stats_collection_frequency = gui.slider_int('Collection Frequency (frames)', self.gamePreset.stats_collection_frequency, 1, 300)
        self.gamePreset.position_collection_frequency = gui.slider_int('Position Frequency (frames)', self.gamePreset.position_collection_frequency, 1, 600)

        gui.text('')
        gui.text('Projectiles parameters:', color=TEXT_COLOR_DARK_GRAY)
        self.gamePreset.projectile_damage = gui.slider_int('Damage', self.gamePreset.projectile_damage, 1, self.gamePreset.drone_max_health)
        self.gamePreset.projectile_speed = gui.slider_int('Speed', self.gamePreset.projectile_speed, 1, 100)
        self.gamePreset.projectile_radius = gui.slider_int('Radius', self.gamePreset.projectile_radius, 1, 5)
        self.gamePreset.projectile_max_lifetime = gui.slider_float('Max Lifetime', self.gamePreset.projectile_max_lifetime, 0.5, 10)

    def _render_planning_menu(self) -> None:
            self.canvas.set_background_color(MENU_BACKGROUND_COLOR)
            gui = self.window.get_gui()

            if not hasattr(self, 'planning_border_field'):
                self.planning_border_field = ti.Vector.field(2, dtype=ti.f32, shape=8)
                self.planning_path_field = ti.Vector.field(2, dtype=ti.f32, shape=2000)
                self.planning_ai_path_field = ti.Vector.field(2, dtype=ti.f32, shape=2000)
                self.planning_start_pos = ti.Vector.field(2, dtype=ti.f32, shape=2)
                self.planning_start_col = ti.Vector.field(3, dtype=ti.f32, shape=2)
                self.planning_start_col[0] = ATTACKING_TEAM_COLOR 
                self.planning_start_col[1] = DEFENDING_TEAM_COLOR 
                
            with gui.sub_window('Mission Planning', 0.05, 0.05, 0.3, 0.9):
                self._render_common_planning_parameters(gui)
                
                gui.text('')
                gui.text('Path Planning:', color=TEXT_COLOR_LIGHT_GRAY)
                if self.multirun_path_mode == 0:
                    gui.text('LMB: Draw Attacking Path (Green)', color=ATTACKING_TEAM_COLOR)
                else:
                    gui.text('Attacking path is generated automatically.', color=ATTACKING_TEAM_COLOR)
                gui.text('RMB: Draw Defending Path (Red)', color=DEFENDING_TEAM_COLOR)

                if gui.button('Reset Attack'): self.gamePreset.attacking_path = []; self.planning_path_field.fill(0)
                if gui.button('Reset AI'): self.gamePreset.ai_path = []; self.planning_ai_path_field.fill(0)
                if gui.button('Reset All'): self._reset_planning_fields()
                if gui.button('Save Scenario'): gui.text("Saved successfully.") if not FileManager().create_config(self.gamePreset.generate_config_dict()) else gui.text('Failed to save scenario.', color=TEXT_DEFEAT_COLOR)
                if gui.button('Load Scenario'): self.gamePreset.load_config(FileManager().load_config())
                
                if gui.button('Visualize Saved Positions'):
                    from modules.statistics import StatisticsLogger
                    StatisticsLogger.show_positions_from_file(self.gamePreset.map_size)
                
                gui.text('')
                if self.gamePreset.ai_path == []: 
                    gui.text('Please draw an AI path.', color=TEXT_DEFEAT_COLOR)
                elif self.multirun_path_mode == 0 and self.gamePreset.attacking_path == []: 
                    gui.text('Please draw an attack path.', color=TEXT_DEFEAT_COLOR)
                elif gui.button('Start Simulation'): 
                    if self.multirun_total_runs > 1:
                        self._start_multirun()
                    else:
                        self._start_game()

            window_shape = self.window.get_window_shape()
            aspect_ratio = window_shape[0] / window_shape[1]
            
            sq_h = 0.7
            sq_w = sq_h / aspect_ratio
            sq_x = 0.45 
            
            min_x, min_y = sq_x, 0.2
            max_x, max_y = sq_x + sq_w, 0.2 + sq_h

            self._draw_planning_border(min_x, min_y, max_x, max_y)
            self._draw_planning_start_positions(min_x, min_y, sq_w, sq_h)
            self._handle_planning_mouse_input(min_x, min_y, max_x, max_y)
            self._draw_planning_paths(min_x, min_y, max_x, max_y)

    def _draw_planning_border(self, min_x: float, min_y: float, max_x: float, max_y: float) -> None:
        self.planning_border_field[0] = [min_x, min_y]; self.planning_border_field[1] = [max_x, min_y]
        self.planning_border_field[2] = [max_x, min_y]; self.planning_border_field[3] = [max_x, max_y]
        self.planning_border_field[4] = [max_x, max_y]; self.planning_border_field[5] = [min_x, max_y]
        self.planning_border_field[6] = [min_x, max_y]; self.planning_border_field[7] = [min_x, min_y]
        self.canvas.lines(self.planning_border_field, width=0.005, color=(1, 1, 1))

    def _draw_planning_start_positions(self, min_x: float, min_y: float, sq_w: float, sq_h: float) -> None:
        self.planning_start_pos[0] = [min_x + (0.1 * sq_w), min_y + (0.5 * sq_h)] # Attacking Team
        self.planning_start_pos[1] = [min_x + (0.9 * sq_w), min_y + (0.5 * sq_h)] # Defending Team
        self.planning_path_field[0] = self.planning_start_pos[0]
        self.planning_ai_path_field[0] = self.planning_start_pos[1]
        self.canvas.circles(self.planning_start_pos, radius=0.015, per_vertex_color=self.planning_start_col)

    def _handle_planning_mouse_input(self, min_x: float, min_y: float, max_x: float, max_y: float) -> None:
        cx = (min_x + max_x) / 2.0
        cy = (min_y + max_y) / 2.0
        rx = (max_x - min_x) / 2.0
        ry = (max_y - min_y) / 2.0

        if self.window.is_pressed(LMB) and self.multirun_path_mode == 0:
            if len(self.gamePreset.attacking_path) == 0:
                start_pt = self.planning_start_pos[0]
                self.gamePreset.attacking_path.append((float((start_pt[0] - cx) / rx), float((start_pt[1] - cy) / ry), 0.5, None))
            self._try_add_path_point(self.gamePreset.attacking_path, min_x, min_y, max_x, max_y, is_attack=True)

        if self.window.is_pressed(RMB):
            if len(self.gamePreset.ai_path) == 0:
                start_pt = self.planning_start_pos[1]
                self.gamePreset.ai_path.append((float((start_pt[0] - cx) / rx), float((start_pt[1] - cy) / ry), 0.5))
            self._try_add_path_point(self.gamePreset.ai_path, min_x, min_y, max_x, max_y, is_attack=False)

    def _try_add_path_point(self, path: list, min_x: float, min_y: float, max_x: float, max_y: float, is_attack: bool = False) -> None:
        curr_mouse = self.window.get_cursor_pos()
        if min_x <= curr_mouse[0] <= max_x and min_y <= curr_mouse[1] <= max_y:
            
            # Map screen position to relative center (-1 to 1 with 0,0 at center)
            cx = (min_x + max_x) / 2.0
            cy = (min_y + max_y) / 2.0
            rx = (max_x - min_x) / 2.0
            ry = (max_y - min_y) / 2.0
            
            # Normalized relative position:
            rel_x = float((curr_mouse[0] - cx) / rx)
            rel_y = float((curr_mouse[1] - cy) / ry)

            if len(path) > 0:
                last_pt = path[-1]
                dist_sq = (rel_x - last_pt[0])**2 + (rel_y - last_pt[1])**2
                if dist_sq < 0.001: 
                    return
            if is_attack:
                path.append((rel_x, rel_y, 0.5, None))
            else:
                path.append((rel_x, rel_y, 0.5))

    def _draw_planning_paths(self, min_x: float, min_y: float, max_x: float, max_y: float) -> None:
        cx = (min_x + max_x) / 2.0
        cy = (min_y + max_y) / 2.0
        rx = (max_x - min_x) / 2.0
        ry = (max_y - min_y) / 2.0
        
        if self.multirun_path_mode == 3 and hasattr(self, 'multirun_paths') and len(self.multirun_paths) > 0:
            colors = [
                (1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1), (0, 1, 1),
                (1, 0.5, 0), (0.5, 0, 1), (0, 0.5, 1), (0.5, 1, 0)
            ]
            for idx, p in enumerate(self.multirun_paths):
                path_len = len(p)
                if path_len > 1:
                    segments_to_draw = min(path_len - 1, 1000)
                    for i in range(segments_to_draw):
                        p_curr = p[i]
                        p_next = p[i+1]
                        self.planning_path_field[2*i] = [p_curr[0] * rx + cx, p_curr[1] * ry + cy]
                        self.planning_path_field[2*i+1] = [p_next[0] * rx + cx, p_next[1] * ry + cy]
                    color = colors[idx % len(colors)]
                    self.canvas.lines(self.planning_path_field, width=0.003, color=color)
        else:
            path_len = len(self.gamePreset.attacking_path)
            if path_len > 1:
                segments_to_draw = min(path_len - 1, 1000)
                for i in range(segments_to_draw):
                    p_curr = self.gamePreset.attacking_path[i]
                    p_next = self.gamePreset.attacking_path[i+1]
                    self.planning_path_field[2*i] = [p_curr[0] * rx + cx, p_curr[1] * ry + cy]
                    self.planning_path_field[2*i+1] = [p_next[0] * rx + cx, p_next[1] * ry + cy]
                self.canvas.lines(self.planning_path_field, width=0.003, color=ATTACKING_TEAM_COLOR)

        ai_path_len = len(self.gamePreset.ai_path)
        if ai_path_len > 1:
            segments_to_draw = min(ai_path_len - 1, 1000)
            for i in range(segments_to_draw):
                p_curr = self.gamePreset.ai_path[i]
                p_next = self.gamePreset.ai_path[i+1]
                self.planning_ai_path_field[2*i] = [p_curr[0] * rx + cx, p_curr[1] * ry + cy]
                self.planning_ai_path_field[2*i+1] = [p_next[0] * rx + cx, p_next[1] * ry + cy]
            self.canvas.lines(self.planning_ai_path_field, width=0.003, color=DEFENDING_TEAM_COLOR)


    def _generate_multirun_path(self) -> None:
        self.multirun_paths = []
        if self.multirun_path_mode == 0:
            pass # Keep manual path
        elif self.multirun_path_mode == 1:
            self.planning_path_field.fill(0)
            self.gamePreset.attacking_path = [
                (-0.7, 0.0, 0.5, DroneModes.ATTACK),
                (0.7, 0.0, 0.5, DroneModes.SPREAD),
                (-0.7, 0.0, 0.5, DroneModes.ATTACK)
            ]
            self.multirun_paths = [self.gamePreset.attacking_path] * self.multirun_total_runs
        elif self.multirun_path_mode == 2:
            self.gamePreset.attacking_path = []
            self.planning_path_field.fill(0)
            pts = 8
            for i in range(pts):
                angle = 2 * math.pi * i / pts
                rx = float(math.cos(angle) * 0.7)
                ry = float(math.sin(angle) * 0.7)
                self.gamePreset.attacking_path.append((rx, ry, 0.5, DroneModes.ATTACK))
            self.multirun_paths = [self.gamePreset.attacking_path] * self.multirun_total_runs
        elif self.multirun_path_mode == 3:
            self.planning_path_field.fill(0)
            for _ in range(self.multirun_total_runs):
                path = [(-0.8, 0.0, 0.5, DroneModes.ATTACK)] # Start at spawn point
                for _ in range(self.multirun_random_points):
                    rx = float(random.uniform(-0.8, 0.8))
                    ry = float(random.uniform(-0.8, 0.8))
                    mode = random.choice([DroneModes.ATTACK, DroneModes.SPREAD, DroneModes.PATROL])
                    path.append((rx, ry, 0.5, mode))
                self.multirun_paths.append(path)
            if len(self.multirun_paths) > 0:
                self.gamePreset.attacking_path = self.multirun_paths[0].copy()

    def _start_multirun(self) -> None:
        self.multirun_active = True
        self.multirun_current_run = 0

        self.multirun_results = []
        self._next_multirun()

    def _next_multirun(self) -> None:
        if self.multirun_path_mode == 3 and self.multirun_current_run < len(self.multirun_paths):
            self.gamePreset.attacking_path = self.multirun_paths[self.multirun_current_run].copy()
            
        self.multirun_current_run += 1
        self._start_game()

    def _finish_multirun(self) -> None:
        self.multirun_active = False
        self.state = self.STATE_PLANNING
        
        if len(self.multirun_results) == 0:
            return
            
        os.makedirs("stats", exist_ok=True)
        filename = f"stats/multirun_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
        
        with open(filename, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Run", "Win", "Time", "PlayerCount", "EnemyCount", "DamagePlayer", "DamageEnemy", "KDRatio"])
            
            wins = 0
            t_time = 0; t_pc = 0; t_ec = 0; t_dp = 0; t_de = 0; t_kd = 0
            
            for i, res in enumerate(self.multirun_results):
                writer.writerow([
                    i+1, res["win"], f"{res['time']:.2f}", res["p_count"], res["e_count"], 
                    f"{res['d_p']:.2f}", f"{res['d_e']:.2f}", f"{res['kd']:.2f}"
                ])
                if res["win"]: wins += 1
                t_time += res["time"]
                t_pc += res["p_count"]
                t_ec += res["e_count"]
                t_dp += res["d_p"]
                t_de += res["d_e"]
                t_kd += res["kd"]
                
            n = len(self.multirun_results)
            writer.writerow([])
            writer.writerow(["AVERAGES", f"{wins/n*100:.1f}%", f"{t_time/n:.2f}", f"{t_pc/n:.1f}", f"{t_ec/n:.1f}", f"{t_dp/n:.2f}", f"{t_de/n:.2f}", f"{t_kd/n:.2f}"])
            
        print(f"Multirun finished. Saved to {filename}")

    def _process_multirun_end(self, win: bool) -> None:
        if self.gui and hasattr(self.gui, 'stats'):
            stats = self.gui.stats.stats_history
            if len(stats["time"]) > 0:
                res = {
                    "win": win,
                    "time": stats["time"][-1],
                    "p_count": stats["player_count"][-1],
                    "e_count": stats["enemy_count"][-1],
                    "d_p": stats["damage_p"][-1],
                    "d_e": stats["damage_e"][-1],
                    "kd": stats["kd_ratio"][-1]
                }
            else:
                res = {"win": win, "time": 0, "p_count": 0, "e_count": 0, "d_p": 0, "d_e": 0, "kd": 0}
            self.multirun_results.append(res)
            
        self._back_to_main_menu()
        if self.multirun_current_run < self.multirun_total_runs:
            self._next_multirun()
        else:
            self._finish_multirun()

    def _back_to_main_menu(self) -> None:
        if self.gui:
            self.gui.GuiState.PAUSED = True
            if hasattr(self.gui, 'stats'):
                self.gui.stats.save_to_csv()
        self.loader = None
        self.state = self.STATE_PLANNING
        self.loading_frames = 0

    def _start_game(self) -> None:
        self.gamePreset.attacking_path_normalized = self.gamePreset.normalize_to_world_coordinates(self.gamePreset.attacking_path)
        self.gamePreset.ai_path_normalized = self.gamePreset.normalize_to_world_coordinates(self.gamePreset.ai_path)
        
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
        if not self.gui or not hasattr(self.gui, 'stats'):
            return
            
        self.gui.stats.show_plot()

    def _show_spatial_analysis(self) -> None:
        if not self.gui or not hasattr(self.gui, 'stats'):
            return
        
        self.gui.stats.show_positions_plot(self.gamePreset.map_size)

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
            
            if gui.button('Show Spatial Analysis (Last Frame)'):
                self._show_spatial_analysis()
            
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
                
            if gui.button('Show Spatial Analysis (Last Frame)'):
                self._show_spatial_analysis()
        
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
            elif self.gui and self.gui.victory:
                if self.multirun_active:
                    self._process_multirun_end(win=True)
                else:
                    self._render_victory()
                    self.window.show()
            elif self.gui and self.gui.defeat:
                if self.multirun_active:
                    self._process_multirun_end(win=False)
                else:
                    self._render_defeat()
                    self.window.show()
            elif self.gui and self.gui.return_to_menu:
                self._back_to_main_menu()
            else:
                self.gui.update()
                self.canvas.scene(self.scene)
                self.window.show()