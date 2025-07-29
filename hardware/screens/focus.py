from PIL import Image
from hardware.screens.screen import Screen
from hardware.state import ScreenState

from hardware.state import UIState
from observation_context import CameraState

from hardware.renderer import render_many_text, render_image_with_caption
from analyzer import analyzer

class FocusScreen(Screen):

    def __init__(self, ui_state: UIState, camera_state: CameraState):
        super().__init__(ui_state)
        self.camera_state = camera_state

    def setup_input(self):        
        self.screen_input.controls['A']["press"] = self.select
        self.screen_input.controls['B']["press"] = self.alt_select

    def select(self):
        self.ui_state.change_screen(ScreenState.NAVIGATE)

    def alt_select(self):
        self.ui_state.change_screen(ScreenState.MAIN_MENU)

    def render(self):
        if self.camera_state.latest_image is None:
            return render_many_text(["Waiting for first image..."])

        fwhm = analyzer.fwhm_values[-1] if analyzer.fwhm_values else 100.0
        min_fwhm = analyzer.lowest_fwhm if analyzer.lowest_fwhm != float('inf') else 100.0

        return render_image_with_caption(
            self.camera_state.latest_image,
            f"FWHM: {fwhm:.2f}", f"Min FWHM found: {min_fwhm:.2f}"
        )