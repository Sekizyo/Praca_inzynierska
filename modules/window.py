import taichi as ti
from modules.drone import DroneSwarm
from modules.map import Map
from taichi.ui.window import Window as TWindow
from taichi.ui import Canvas, Scene, Camera



class Window():
    PLAYER_COLOR = (1.0, 0.2, 0.2)
    ENEMY_COLOR = (0.2, 0.2, 1.0)
    
    def __init__(self, title="Drone Voronoi Sim", size=(1024, 768)):
        ti.init()
        self.window: TWindow = TWindow(title, size)
        self.canvas: Canvas = self.window.get_canvas()
        self.scene: Scene = Scene()
        self.map = Map()
        
        self._init_camera()
        self._init_swarms()
        
    def _init_camera(self) -> None:
        self.camera: Camera = Camera()
        self.camera.position(0, -150, 100)
        self.camera.lookat(0, 0, 0)
        self.scene.set_camera(self.camera)
    
    def _init_swarms(self) -> None:
        self.player_swarm = DroneSwarm(count=10, boundary_size=100.0)
        # self.enemy_swarm = DroneSwarm(count=10, boundary_size=100.0)
        
    def run(self) -> None:
        while self.window.running:
            self.camera.track_user_inputs(self.window, movement_speed=0.03, hold_key=ti.ui.RMB)
            
            target = ti.Vector([0.0, 0.0, 0.0]) 
            
            self.player_swarm.update(dt=0.05, target_pos=target, mode_weight=1.5)
            
            self.scene.point_light(pos=(0, 0, 100), color=(1, 1, 1))
            
            self.scene.particles(self.player_swarm.get_pos_field(), 
                            per_vertex_color=self.PLAYER_COLOR, 
                            radius=1.0)

            self.scene.lines(self.map.get_boundary_field(), color=(0.0, 1.0, 0.0), width=2.0)
            
            self.canvas.scene(self.scene)
            self.window.show()
