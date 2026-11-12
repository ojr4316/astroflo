""" State Manager for UI, Controls creating and rendering images, and managing input """
import threading
import time
from hardware.input import Input

from observation_context import ObservationContext
from hardware.state import UIState, ScreenState
from hardware.screen_factory import ScreenFactory

from hardware import renderer
from hardware.renderer import render_many_text
from astronomy.starfield import StarfieldRenderer

init_text = ['\n', '\n', "~ ASTROFLO ~", "Calibrating camera", "and loading modified", "Tycho catalog.", '\n', '\n', "Please wait 5-10 seconds"]

class UIManager:
    def __init__(self, context: ObservationContext, starfield: StarfieldRenderer, display=None, buttons=None):
        """ display: TFTDisplay or VirtualDisplay (default: virtual); buttons: DisplayButtons or SimInput (default: sim) """
        self.state_manager = UIState()
        self.state_manager.change_input = self.change_input
        self.context = context
        self.starfield = starfield
        renderer.status_provider = lambda: context.imaging_state.connected

        self.screen_input = Input()
        if display is None:
            from hardware.virtual_display import VirtualDisplay
            display = VirtualDisplay()
        if buttons is None:
            from hardware.sim_input import SimInput
            buttons = SimInput()
        self.screen = display
        self.buttons = buttons
        self.stop_event = threading.Event()
        self.display_enabled = True
        self.brightness = 0.5
        self.screen.set_brightness(self.brightness)
        self.screen.draw_screen(render_many_text(init_text))

        self.screen_factory = ScreenFactory()

        self.screens = self.screen_factory.build_screens(self.state_manager, self.screen_input, context, starfield)
        self.state_manager.change_screen(ScreenState.MAIN_MENU) # default to main menu

    def change_input(self, state: ScreenState):
        self.screen_input.reset()
        self.screens[state].setup_input()

    def set_display(self, enabled: bool = None, brightness: float = None):
        """ Turn the TFT on/off (backlight + rendering) and/or set brightness """
        if brightness is not None:
            self.brightness = max(0.0, min(1.0, float(brightness)))
            self.screen.set_brightness(self.brightness)
        if enabled is not None and enabled != self.display_enabled:
            self.display_enabled = bool(enabled)
            if not self.display_enabled:
                self.screen.clear()
            self.screen.set_backlight(self.display_enabled)

    def set_screen(self, state: ScreenState):
        self.state_manager.change_screen(state)

    def current_screen(self):
        return self.screens[self.state_manager.state]

    def render(self):
        return self.current_screen().render()
    
    def handle_input(self):
        while not self.stop_event.is_set():
            self.buttons.read_buttons(self.screen_input)
            time.sleep(0.01)

    def draw_once(self):
        if self.display_enabled:
            self.screen.draw_screen(self.render())

    def draw_screen(self):
        """ Render loop for the TFT or the virtual display """
        while not self.stop_event.is_set():
            if self.display_enabled:
                try:
                    self.draw_once()
                except Exception as e:  # keep the loop alive if one screen fails to render
                    print(f"Screen render failed: {e}")
                    time.sleep(0.5)
            else:
                time.sleep(0.2) # Display off: skip rendering, save CPU
            time.sleep(0.01)

    def stop(self):
        self.stop_event.set()
