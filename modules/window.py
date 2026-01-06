import taichi as ti
from taichi.ui.window import Window as TWindow
from taichi.ui import Canvas
from modules.gui import GUI


class Window():
    MAP_SIZE: float = 250.0
    
    def __init__(self, title="Drone Voronoi Sim", size=(1920, 1000)) -> None:
        ti.init(offline_cache=True)
        self.window: TWindow = TWindow(title, size, pos=(0,30),show_window=True)
        self.canvas: Canvas = self.window.get_canvas()
        self.scene = self.window.get_scene()
        self.gui = GUI(self.window.get_gui(), self.window, self.scene)
        self.loader = self.gui.load()
        self.is_loading = True
        self.loading_text = "Starting..."
        self.loading_frames = 0

    def render_loading(self):
        self.canvas.set_background_color((0, 0, 0))
        with self.window.get_gui().sub_window("Loading", 0.4, 0.45, 0.2, 0.1):
            self.window.get_gui().text(f"{self.loading_text}{'.' * ((self.loading_frames // 10) % 4)}", color=(1, 1, 1))
    
    def run(self) -> None:
        while self.window.running:
            if self.is_loading:
                self.render_loading()
                self.window.show()
                self.loading_frames += 1
                
                # Process one loading step per frame
                try:
                    self.loading_text = next(self.loader)
                except StopIteration:
                    self.is_loading = False
            else:
                self.gui.update()
                self.canvas.scene(self.scene)
                self.window.show()
