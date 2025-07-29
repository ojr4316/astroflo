import time
from hardware.screens.screen import Screen
from utils import distance_descriptor, radec_to_altaz
from hardware.state import ScreenState

from hardware.state import UIState
from observation_context import TelescopeState, TargetState, SolverState, Environment

from hardware.renderer import render_many_text

class DirectionsScreen(Screen):

    def __init__(self, ui_state: UIState, screen_input, env: Environment, telescope_state: TelescopeState, target_state: TargetState, solver_state: SolverState):
        super().__init__(ui_state, screen_input)
        self.telescope_state = telescope_state
        self.target_state = target_state
        self.solver_state = solver_state

    def setup_input(self):
        self.screen_input.controls['B']["press"] = self.alt_select

    def alt_select(self):
        self.ui_state.change_screen(ScreenState.NAVIGATE)

    def render(self):
        if self.telescope_state.position is None:
            return render_many_text(["Waiting for first solve..."])

        if self.target_state.has_target():
            target_name = self.target_state.name
            target_ra = self.target_state.ra
            target_dec = self.target_state.dec
            ra, dec = self.telescope_state.position
            alt, az = radec_to_altaz(ra, dec, self.env.astropy_time(), self.env.astropy_location)
            target_alt, target_az = radec_to_altaz(target_ra, target_dec, self.env.astropy_time(), self.env.astropy_location)

            delta_x = target_az - az
            delta_y = target_alt - alt

            north = f"North: {distance_descriptor(delta_y)} ({delta_y:.2f}°)"
            east = f"East: {distance_descriptor(delta_x)} ({delta_x:.2f}°)"

            return render_many_text(['\n', 'CURRENT TARGET:', target_name, '\n', north, '\n', east, '\n', f"Last Solve: {(time.time()-self.solver_state.last_solved):.1f}s"])
        return render_many_text(["No target set."])

    
