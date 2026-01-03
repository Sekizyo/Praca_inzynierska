import taichi as ti
from taichi.ui.window import Window as TWindow
from taichi.ui import Canvas
from modules.gui import GUI


class Window():
    MAP_SIZE: float = 250.0
    
    def __init__(self, title="Drone Voronoi Sim", size=(1920, 1000)) -> None:
        ti.init(offline_cache=True)
        self.window: TWindow = TWindow(title, size, pos=(0,30),show_window=True, vsync=True, fps_limit=120)
        self.canvas: Canvas = self.window.get_canvas()
        self.scene = self.window.get_scene()
        self.gui = GUI(self.window.get_gui(), self.window, self.scene)
    
    def run(self) -> None:
        while self.window.running:
            self.gui.update()
            self.canvas.scene(self.scene)
            self.window.show()
