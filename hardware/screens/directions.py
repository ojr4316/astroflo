import time
from hardware.screens.screen import Screen
from utils import distance_north_east, distance_descriptor, radec_to_altaz, altaz_to_radec
from hardware.state import ScreenState

class DirectionsScreen(Screen):

    def __init__(self, ui):
        super().__init__(ui)

    def setup_input(self):
        self.screen_input.controls['B']["press"] = self.alt_select

    def alt_select(self):
        self.ui.change_screen(ScreenState.NAVIGATE)

    def render(self):
        scope = self.pipeline.scope
        if scope.position is None:
            return self.renderer.render_many_text(["Waiting for first solve..."])

        if scope.target_manager.has_target():
            target_name = scope.target_manager.name
            target_ra, target_dec = scope.target_manager.get_target_position()
            ra, dec = scope.get_position()
            alt, az = radec_to_altaz(ra, dec, scope.astropy_time(), scope.location)
            target_alt, target_az = radec_to_altaz(target_ra, target_dec, scope.astropy_time(), scope.location)

            delta_x = target_az - az
            delta_y = target_alt - alt

            north = f"North: {distance_descriptor(delta_y)} ({delta_y:.2f}°)"
            east = f"East: {distance_descriptor(delta_x)} ({delta_x:.2f}°)"

            return self.renderer.render_many_text(['\n', 'CURRENT TARGET:', target_name, '\n', north, '\n', east, '\n', f"Last Solve: {(time.time()-self.pipeline.latest_timestamp):.1f}s"])
        return self.renderer.render_many_text(["No target set."])

    
