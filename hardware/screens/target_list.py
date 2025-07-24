from hardware.screens.screen import Screen
from hardware.state import ScreenState

class TargetList(Screen):

    def __init__(self, ui):
        super().__init__(ui)
        self.title = "Target Lists"
        self.scope = ui.scope
        self.mag_limit = 6
        self.only_dsos = True
        self.selected_y = 0
        self.options = ["Bright Stars", "Messier", "Solar System"]
        self.max_y = len(self.options) - 1

    def setup_input(self):
        self.screen_input.controls['R']["press"] = self.up
        self.screen_input.controls['L']["press"] = self.down

        self.screen_input.controls['A']["press"] = self.select
        self.screen_input.controls['B']["press"] = self.alt_select

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

    def select(self):
        # TODO: communicate to separate ui screen about selected target list
        self.ui.selected_catalog = self.selected_y
        self.ui.change_screen(ScreenState.TARGET_SELECT)

    def alt_select(self):
        self.ui.change_screen(ScreenState.MAIN_MENU)

    def render(self):
        return self.renderer.render_menu(f"{self.title}", self.options, self.selected_y)