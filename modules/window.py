import taichi as ti


class Window():
    def __init__(self, title="Taichi Window", size=(800, 600), vsync=True):
        ti.init()
        self.window = ti.ui.Window(title, size, vsync=vsync)
        self.canvas = self.window.get_canvas()
        self.scene = ti.ui.Scene()
        self.camera = ti.ui.Camera()

    def get_window(self):
        return self.window

    def get_canvas(self):
        return self.canvas

    def get_scene(self):
        return self.scene

    def get_camera(self):
        return self.camera

    def run(self) -> None:
        num_particles = 100
        particles = ti.Vector.field(3, dtype=float, shape=num_particles)

        @ti.kernel
        def init_particles():
            for i in range(num_particles):

                particles[i] = [ti.random() - 0.5, ti.random() - 0.5, ti.random() - 0.5]

        init_particles()

        while self.get_window().running:
            # Update camera
            self.camera.track_user_inputs(self.window, movement_speed=0.03, hold_key=ti.ui.RMB)
            self.scene.set_camera(self.camera)

            # Lighting
            self.scene.point_light(pos=(0, 1, 2), color=(1, 1, 1))
            self.scene.ambient_light((0.5, 0.5, 0.5))

            # Render particles
            self.scene.particles(particles, radius=0.05, color=(0.5, 0.42, 0.8))

            self.canvas.scene(self.scene)
            self.window.show()
