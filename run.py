from modules.window import Window


if __name__ == "__main__":
    window: Window = Window(title="Taichi", size=(800, 600), vsync=True)
    window.run()