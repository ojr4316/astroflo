import time

from hardware.screens.screen import Screen
from hardware.state import ScreenState, UIState
from hardware.renderer import render_button_panel
from observation_context import ImagingState, TargetState

RESULT_DISPLAY_S = 2.0


class ImagingScreen(Screen):
    """ Imaging camera controls: Auto on/off toggle and a manual Capture button. """

    BACK, AUTO, CAPTURE = 0, 1, 2

    def __init__(self, ui_state: UIState, screen_input, imaging_state: ImagingState, target_state: TargetState):
        super().__init__(ui_state, screen_input)
        self.imaging_state = imaging_state
        self.target_state = target_state
        self.selected = self.AUTO
        self.max_idx = self.CAPTURE

    def setup_input(self):
        self.screen_input.controls['R']["press"] = self.up
        self.screen_input.controls['L']["press"] = self.down
        self.screen_input.controls['A']["press"] = self.select
        self.screen_input.controls['B']["press"] = self.back

    def up(self):
        self.selected = self.selected - 1 if self.selected > 0 else self.max_idx

    def down(self):
        self.selected = self.selected + 1 if self.selected < self.max_idx else 0

    def back(self):
        self.ui_state.change_screen(ScreenState.MAIN_MENU)

    def toggle_auto(self):
        self.imaging_state.auto_enabled = not self.imaging_state.auto_enabled

    def capture(self):
        self.imaging_state.manual_requested.set()

    def select(self):
        match self.selected:
            case self.BACK: self.back()
            case self.AUTO: self.toggle_auto()
            case self.CAPTURE: self.capture()

    def status_lines(self):
        s = self.imaging_state
        exposure_ms = s.exposure_us / 1000
        exposure = f"{exposure_ms:.1f}ms" if exposure_ms < 1000 else f"{exposure_ms / 1000:.2f}s"
        target = self.target_state.name if self.target_state.has_target() else "none"
        lines = [
            f"Camera: {'connected' if s.connected else 'disconnected'}",
            f"Exp: {exposure}  Gain: {s.gain:.0f}",
            f"Target: {target} ({'in field' if s.target_in_field else 'not in field'})",
            f"Saved: {s.frames_saved}",
        ]
        if s.manual_requested.is_set():
            lines.append("Capturing...")
        elif s.last_result and time.time() - s.last_result_time < RESULT_DISPLAY_S:
            lines.append(s.last_result)
        return lines

    def render(self):
        buttons = [f"Auto: {'On' if self.imaging_state.auto_enabled else 'Off'}", "Capture"]
        return render_button_panel("Imaging", buttons, self.selected, self.status_lines())
