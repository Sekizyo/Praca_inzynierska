import taichi as ti
import threading
from typing import Optional
from taichi.ui.canvas import SceneV2
from taichi.ui.window import Window as TWindow
from taichi.ui import Canvas
from modules.gui import GUI
from modules.colors import *


class Window():
    MAP_SIZE: float = 250.0
    DRONE_PRESETS: list[int] = [500, 1000, 2000, 4000, 8000]
    STATE_MENU: int = 0
    STATE_LOADING: int = 1
    STATE_GAME: int = 2
    STATE_VICTORY: int = 3
    STATE_DEFEAT: int = 4
    
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
                    self.drone_count = preset

            gui.text('')
            gui.text(f'Selected: {self.drone_count} drones per team', color=TEXT_COLOR_GREEN)
            gui.text(f'Total drones: {self.drone_count * 2}', color=TEXT_COLOR_GREEN)
            gui.text('')

            if gui.button('Start Game'):
                self._start_game()

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

    def _start_game(self) -> None:
        self.state = self.STATE_LOADING
        if self.gui is not None and self.gui.drone_count == self.drone_count:
            self.canvas.set_background_color((0, 0, 0))
            self.gui.reset()
            self.state = self.STATE_GAME
            return
        
        self.gui = GUI(self.window.get_gui(), self.window, self.scene, self.drone_count)
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
            gui.text(f'Drones used: {self.drone_count} per team', color=TEXT_COLOR_GRAY)
            gui.text('')
            
            if gui.button('Return to Main Menu'):
                self.gui.GuiState.PAUSED = True
                self.loader = None
                self.state = self.STATE_MENU
                self.loading_frames = 0

    def _render_defeat(self) -> None:
        self.canvas.set_background_color(MENU_BACKGROUND_DEFEAT_COLOR)
        gui = self.window.get_gui()
        
        with gui.sub_window('Defeat', 0.3, 0.3, 0.4, 0.4):
            gui.text('DEFEAT', color=TEXT_DEFEAT_COLOR)
            gui.text('')
            gui.text('Your forces have been eliminated!', color=TEXT_COLOR_WHITE)
            gui.text('')
            gui.text(f'Drones used: {self.drone_count} per team', color=TEXT_COLOR_GRAY)
            gui.text('')
            
            if gui.button('Return to Main Menu'):
                self.gui.GuiState.PAUSED = True
                self.loader = None
                self.state = self.STATE_MENU
                self.loading_frames = 0

    def run(self) -> None:
        while self.window.running:
            if self.state == self.STATE_MENU:
                self._render_menu()
                self.window.show()
            elif self.state == self.STATE_LOADING:
                self._render_loading()
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
