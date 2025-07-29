from hardware.screens.screen import Screen
from hardware.state import ScreenState

from hardware.state import UIState
from hardware.renderer import render_menu
from observation_context import TargetState, Environment
from astronomy.catalog import Catalog

class TargetSelect(Screen):

    def __init__(self, ui_state: UIState, screen_input, environment: Environment, catalog: Catalog, target_state: TargetState):
        super().__init__(ui_state, screen_input)
        self.environment = environment
        self.catalog = catalog
        self.target_state = target_state
        self.mag_limit = 4
        self.selected_y = 0
        self.options = []
        self.names = []

    def build_options(self):
        match self.target_state.catalog_filter:
            case 0:
                self.options = self.catalog.get_bright_stars(self.mag_limit)
            case 1:
                self.options = self.catalog.get_dsos(self.mag_limit)
            case 2:
                self.options = self.catalog.get_solar_system()
        if len(self.options) > 0:
            self.names = [target['Name'] for target in self.options]
        
        self.max_y = len(self.options) - 1
        if self.selected_y > self.max_y:
            self.selected_y = 0

    def setup_input(self):
        self.build_options()
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

    def down(self):
        if self.selected_y < self.max_y:
            self.selected_y += 1
        else:
            self.selected_y = 0

    def select(self):
        if self.selected_y > self.max_y:
            print("ERROR: Target selected is out of bounds")
            return
        self.target_state.set_target(
            self.options[self.selected_y]['RAdeg'],
            self.options[self.selected_y]['DEdeg'],
            self.options[self.selected_y]['Name']
        )
        self.ui_state.change_screen(ScreenState.NAVIGATE)

    def alt_select(self):
        self.ui_state.change_screen(ScreenState.MAIN_MENU)

    def render(self):
        return render_menu(f"{f'>{self.mag_limit} ' if self.target_state.catalog_filter != 2 else ''}Target?", self.names, self.selected_y)

    def increase(self):
        if self.mag_limit < 10:
            self.mag_limit += 0.5
        else:
            self.mag_limit = 10
        self.build_options()

    def decrease(self):
        if self.mag_limit >= 0.5:
            self.mag_limit -= 0.5
        else:
            self.mag_limit = 0
        self.build_options()