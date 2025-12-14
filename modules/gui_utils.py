class GuiState(str):
    def __init__(self) -> None:
        self.PAUSED: bool = False
        self.SHOW_VORONOI: bool = False
        self.SHOW_SHOOT_RANGE: bool = False
        self.SHOW_BOUNDARY: bool = True
