from PIL import Image
from hardware.screens.screen import Screen
from hardware.state import ScreenState

class DebugHardware(Screen):

    def setup_input(self):
        self.pipeline.configuring = True # enable camera capture, no solve
        
        self.screen_input.controls['A']["press"] = self.select
        self.screen_input.controls['B']["press"] = self.alt_select

    def select(self):
        self.ui.change_screen(ScreenState.NAVIGATE)

    def alt_select(self):
        self.ui.change_screen(ScreenState.MAIN_MENU)

    def render(self):
        if not self.pipeline.configuring:
            self.pipeline.configuring = True
        if self.pipeline.latest_image is None:
            return self.renderer.render_many_text(["Waiting for first image..."])
        fwhm = self.pipeline.analysis.fwhm_values[-1]  if len(self.pipeline.analysis.fwhm_values) > 0 else 1000
        min_fwhm = min(self.pipeline.analysis.fwhm_values) if self.pipeline.analysis.fwhm_values else 0.0

        return self.renderer.render_image_with_caption(
            self.pipeline.latest_image if self.pipeline.latest_image is not None else Image.new("RGB", (240, 240)),
            f"FWHM: {fwhm:.2f}", f"Min FWHM found: {min_fwhm:.2f}"
        )