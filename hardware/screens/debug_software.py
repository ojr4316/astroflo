import pytz
from hardware.screens.screen import Screen
from hardware.state import ScreenState

class DebugSoftware(Screen):

    def setup_input(self):
        self.screen_input.controls['A']["press"] = self.select
        self.screen_input.controls['B']["press"] = self.alt_select

    def select(self):
        self.ui.change_screen(ScreenState.NAVIGATE)

    def alt_select(self):
        self.ui.change_screen(ScreenState.MAIN_MENU)

    def render(self):
        scope = self.pipeline.scope
        t = scope.get_time()
        location = scope.location

        local = pytz.timezone("America/New_York")
        local_time = t.astimezone(local)
        julian_date = t.tt
        utc = t.utc_strftime()

        lst = (t.gast + location.lon.degree / 15.0) % 24.0

        position = scope.get_position()

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
            f"Lens: {scope.eyepiece}mm ({scope.eyepiece_fov}° AFOV)",
            f"APT: {scope.aperture}mm FL: {scope.focal_length}mm",
        ]

        if not hasattr(self.pipeline, "analysis"):
            return self.renderer.render_many_text(screen_text)

        latest_analysis = self.pipeline.analysis.get_latest()
        if latest_analysis is not None:
            lines = str(latest_analysis).replace('"', '').replace("{", "").replace("}", '').split(",")
            screen_text = lines + screen_text

        return self.renderer.render_many_text(screen_text)