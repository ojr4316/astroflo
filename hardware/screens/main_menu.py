from hardware.screens.screen import Screen
from hardware.state import ScreenState

class MainMenu(Screen):

    def __init__(self, ui):
        super().__init__(ui)
        self.title = "~astroflo"
        self.options = ["Target Select", "Directions", "Navigate"]
        self.selected_y = 0
        self.max_y = len(self.options) - 1

    def setup_input(self):
        self.screen_input.controls['R']["press"] = self.up
        self.screen_input.controls['L']["press"] = self.down

        self.screen_input.controls['A']["press"] = self.select
        self.screen_input.controls['B']["press"] = self.alt_select

    def select(self):
        match self.selected_y:
            case 0: self.ui.change_screen(ScreenState.TARGET_LIST)
            case 1: self.ui.change_screen(ScreenState.DIRECTION)
            case 2: self.ui.change_screen(ScreenState.NAVIGATE)

    def alt_select(self):
        self.ui.change_screen(ScreenState.DEBUG_SOFTWARE)

    def render(self):
        return self.renderer.render_menu(self.title, self.options, self.selected_y)
    
    def up(self):        
        if self.selected_y > 0:
            self.selected_y -= 1
        else:
            self.selected_y = self.max_y

    def down(self):
        if self.selected_y < self.max_y:
            self.selected_y += 1
        else:
            self.selected_y = 0