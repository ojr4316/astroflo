from hardware.screens.info import InfoScreen
from hardware.screens.focus import FocusScreen
from hardware.screens.main_menu import MainMenu
from hardware.screens.navigation import NavigationScreen
from hardware.screens.directions import DirectionsScreen
from hardware.screens.alignment import AlignmentScreen
from hardware.screens.target_list import TargetList
from hardware.screens.target_select import TargetSelect

from hardware.state import UIState, ScreenState
from observation_context import ObservationContext
from astronomy.starfield import StarfieldRenderer
from hardware.input import Input

class ScreenFactory:
    @staticmethod
    def build_screens(ui_state: UIState, screen_input: Input, ctx: ObservationContext, starfield: StarfieldRenderer):
        return {
            ScreenState.MAIN_MENU: MainMenu(ui_state, screen_input),
            ScreenState.INFO: InfoScreen(ui_state, screen_input, ctx.environment, ctx.telescope_state, ctx.telescope_optics, ctx.target_state, ctx.solver_state),
            ScreenState.FOCUS: FocusScreen(ui_state, screen_input, ctx.camera_state),
            ScreenState.NAVIGATE: NavigationScreen(ui_state, screen_input, ctx.telescope_state, ctx.telescope_optics, ctx.target_state, ctx.solver_state, starfield),
            ScreenState.DIRECTIONS: DirectionsScreen(ui_state, screen_input, ctx.environment, ctx.telescope_state, ctx.target_state, ctx.solver_state),
            ScreenState.ALIGNMENT: AlignmentScreen(ui_state, screen_input, ctx.camera_state, ctx.solver_state),
            ScreenState.TARGET_LIST: TargetList(ui_state, screen_input, ctx.environment, ctx.target_state),
            ScreenState.TARGET_SELECT: TargetSelect(ui_state, screen_input, ctx.environment, starfield.catalog, ctx.target_state)
        }
