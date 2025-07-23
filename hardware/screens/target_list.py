from hardware.screens.screen import Screen
from hardware.state import ScreenState

class TargetList(Screen):

    def __init__(self, ui):
        super().__init__(ui)
        self.title = "Targets"
        self.scope = ui.scope
        self.mag_limit = 6
        self.only_dsos = True
        self.selected_y = 0
        self.build_options()

    def build_options(self):
        self.options = self.scope.get_sky(self.mag_limit, self.only_dsos)
        self.names = [target['Name'] for target in self.options]
        self.max_y = len(self.options) - 1
        if self.selected_y > self.max_y:
            self.selected_y = 0

    def setup_input(self):
        self.screen_input.controls['R']["press"] = self.up
        self.screen_input.controls['L']["press"] = self.down

        self.screen_input.controls['U']["press"] = self.decrease
        self.screen_input.controls['D']["press"] = self.increase

        self.screen_input.controls['A']["press"] = self.select
        self.screen_input.controls['B']["press"] = self.alt_select

    def up(self):
        if self.selected_y > 0:
            self.selected_y -= 1
        else:
            self.selected_y = self.max_y
        self.build_options()

    def down(self):
        if self.selected_y < self.max_y:
            self.selected_y += 1
        else:
            self.selected_y = 0
        self.build_options()

    def select(self):
        self.scope.target_manager.set_target(
            self.options[self.selected_y]['RAdeg'],
            self.options[self.selected_y]['DEdeg'],
            self.options[self.selected_y]['Name']
        )
        self.ui.change_screen(ScreenState.NAVIGATE)

    def alt_select(self):
        self.ui.change_screen(ScreenState.MAIN_MENU)

    def render(self):
        return self.renderer.render_menu(f"{self.title} ({self.mag_limit}|{not self.only_dsos})", self.names, self.selected_y)
    
    def increase(self):        
        if self.mag_limit < 10:
            self.mag_limit += 0.5
        else:
            self.mag_limit = 10

    def decrease(self):
        if self.mag_limit >= 0.5:
            self.mag_limit -= 0.5
        else:
            self.mag_limit = 0