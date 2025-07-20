from hardware.screens.screen import Screen
from hardware.state import ScreenState

class MainMenu(Screen):

    def __init__(self, ui):
        super().__init__(ui)
        self.title = "~astroflo"
        self.options = ["Target Select", "Directions", "Navigate"]
        self.max_y = len(self.options) - 1

    def select(self):
        match self.selected_y:
            case 0: self.ui.change_screen(ScreenState.TARGET_LIST)
            case 1: self.ui.change_screen(ScreenState.DIRECTION)
            case 2: self.ui.change_screen(ScreenState.NAVIGATE)

    def render(self):
        return self.renderer.render_menu(self.title, self.options, self.selected_y)