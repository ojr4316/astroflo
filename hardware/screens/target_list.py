from hardware.screens.screen import Screen
from hardware.state import ScreenState

from hardware.state import UIState
from hardware.renderer import render_menu
from observation_context import TargetState, Environment

class TargetList(Screen):

    def __init__(self, ui_state: UIState, screen_input, environment: Environment, target_state: TargetState):
        super().__init__(ui_state, screen_input)
        self.environment = environment
        self.target_state = target_state
        self.mag_limit = 6
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
        self.target_state.catalog_filter = self.selected_y
        self.ui_state.change_screen(ScreenState.TARGET_SELECT)

    def alt_select(self):
        self.ui_state.change_screen(ScreenState.MAIN_MENU)

    def render(self):
        return render_menu(f"Catalog?", self.options, self.selected_y)