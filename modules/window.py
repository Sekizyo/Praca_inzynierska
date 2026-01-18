import taichi as ti
import threading
import os
import sys
from taichi.ui.window import Window as TWindow
from taichi.ui import Canvas
from modules.gui import GUI


class Window():
    MAP_SIZE: float = 250.0
    
    def __init__(self, title="Drone Voronoi Sim", size=(1920, 1000)) -> None:
        if getattr(sys, 'frozen', False):
            application_path = sys._MEIPASS # If the application is run as a exe
        else:
            application_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        cache_path = os.path.join(application_path, 'ticache')
        os.environ['TI_OFFLINE_CACHE_FILE_PATH'] = str(cache_path)
        
        if not os.path.exists(cache_path):
            os.makedirs(cache_path, exist_ok=True)

        ti.init(arch=ti.vulkan, default_fp=ti.f32, default_ip=ti.i32, offline_cache=True, 
                kernel_profiler=True, advanced_optimization=True, fast_math=True)
        
        self.window: TWindow = TWindow(title, size, pos=(0,30), show_window=True, vsync=False)
        self.canvas: Canvas = self.window.get_canvas()
        self.scene = self.window.get_scene()
        self.gui = GUI(self.window.get_gui(), self.window, self.scene)
        self.loader = self.gui.load()
        self.is_loading = True
        self.loading_text = "Starting"
        self.loading_frames = 0

    def render_loading(self):
        self.canvas.set_background_color((0, 0, 0))
        with self.window.get_gui().sub_window("Loading", 0.4, 0.45, 0.2, 0.1):
            self.window.get_gui().text(f"{self.loading_text}{'.' * ((self.loading_frames // 100) % 4)}", color=(1, 1, 1))
    
    def _run_loader(self):
        for text in self.loader:
            self.loading_text = text
        self.is_loading = False

    def run(self) -> None:
        threading.Thread(target=self._run_loader, daemon=True).start()

        while self.window.running:
            if self.is_loading:
                self.render_loading()
                self.window.show()
                self.loading_frames += 1
            else:
                self.gui.update()
                self.canvas.scene(self.scene)
                self.window.show()
