import time
from hardware.screens.screen import Screen
from utils import distance_north_east, distance_descriptor
from hardware.state import ScreenState

class DirectionsScreen(Screen):

    def __init__(self, ui):
        super().__init__(ui)

    def setup_input(self):
        self.screen_input.controls['B']["press"] = self.alt_select

    def render(self):
        scope = self.pipeline.scope
        if scope.position is None:
            return self.renderer.render_many_text(["Waiting for first solve..."])

        if scope.target_manager.has_target():
            target_name = scope.target_manager.name
            target_ra, target_dec = scope.target_manager.get_target_position()
            ra, dec = scope.get_position()
            north, east = distance_north_east(ra, dec, target_ra, target_dec, scope.viewing_angle)
            north = ("Up" if north >= 0 else "Down") + f" {distance_descriptor(north)} ({abs(north):.2f}°)"
            east = ("Right" if east >= 0 else "Left") + f" {distance_descriptor(east)} ({abs(east):.2f}°)"

            return self.renderer.render_many_text(['\n', 'CURRENT TARGET:', target_name, '\n', north, '\n', east, '\n', f"Last Solve: {(time.time()-self.pipeline.latest_timestamp):.1f}s"])
        return self.renderer.render_many_text(["No target set."])
    
    def alt_select(self):
        self.ui.change_screen(ScreenState.MAIN_MENU)
