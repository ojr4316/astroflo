import pytz
from hardware.screens.screen import Screen
from hardware.state import ScreenState
from hardware.state import UIState
from observation_context import TelescopeState, TelescopeOptics, TargetState, SolverState, Environment

from hardware.renderer import render_many_text
from analyzer import analyzer

class InfoScreen(Screen):

    def __init__(self, ui_state: UIState, environment: Environment, telescope_state: TelescopeState, telescope_optics: TelescopeOptics, target_state: TargetState, solver_state: SolverState):
        super().__init__(ui_state)
        self.environment = environment
        self.telescope_state = telescope_state
        self.telescope_optics = telescope_optics
        self.target_state = target_state
        self.solver_state = solver_state

    def setup_input(self):
        self.screen_input.controls['A']["press"] = self.select
        self.screen_input.controls['B']["press"] = self.alt_select

    def select(self):
        self.ui_state.change_screen(ScreenState.NAVIGATE)

    def alt_select(self):
        self.ui_state.change_screen(ScreenState.MAIN_MENU)

    def render(self):
        t = self.environment.time
        location = self.environment.location

        local = pytz.timezone("America/New_York")
        local_time = t.astimezone(local)
        julian_date = t.tt
        utc = t.utc_strftime()

        lst = (t.gast + location.lon.degree / 15.0) % 24.0

        position = self.telescope_state.position

        pos_str = "Unsolved"
        if position:
            pos_str = f"RA:{position[0]:.4f} | DEC:{position[1]:.4f}"

        screen_text = [
            pos_str,
            f"Local: {local_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"{utc}",
            f"Julian Date: {julian_date:.5f}",
            f"LST: {lst:.2f}h",
            
            f"{location.lat.degree:.4f}°N, {location.lon.degree:.4f}°E",
            f"Lens: {self.telescope_optics.eyepiece}mm ({self.telescope_optics.eyepiece_fov}° AFOV)",
            f"APT: {self.telescope_optics.aperture}mm FL: {self.telescope_optics.focal_length}mm",
        ]

        screen_text.append(f"FWHM: {analyzer.fwhm_values[-1] if analyzer.fwhm_values else 100.0:.2f}")
        screen_text.append(f"BG+NOISE: {analyzer.background_levels[-1] if analyzer.background_levels else 100.0:.2f}+{analyzer.noise_levels[-1] if analyzer.noise_levels else 100.0:.2f}")

        return render_many_text(screen_text)