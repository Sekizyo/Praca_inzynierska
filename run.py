from modules.window import Window


if __name__ == "__main__":
    window: Window = Window(title="Taichi", size=(1024, 768))
    window.run()