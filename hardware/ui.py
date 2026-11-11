""" State Manager for UI, Controls creating and rendering images, and managing input """
import time
import os
from hardware.input import Input
from hardware.adafruit_tft_bonnet import AdafruitTFTBonnet

from observation_context import ObservationContext
from hardware.state import UIState, ScreenState
from hardware.screen_factory import ScreenFactory

from hardware.renderer import render_many_text
from astronomy.starfield import StarfieldRenderer

init_text = ['\n', '\n', "~ ASTROFLO ~", "Calibrating camera", "and loading modified", "Tycho catalog.", '\n', '\n', "Please wait 5-10 seconds"]

class UIManager:
    def __init__(self, context: ObservationContext, starfield: StarfieldRenderer):
        self.state_manager = UIState()
        self.state_manager.change_input = self.change_input
        self.context = context
        self.starfield = starfield

        self.screen_input = Input()
        self.screen = AdafruitTFTBonnet()
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
        while True:
            self.screen.handle_input(self.screen_input)
            time.sleep(0.01)

    def draw_screen(self):
        
        if os.name == 'nt' or os.uname().nodename != "rpi":
            return
        while True:
            if self.display_enabled:
                self.screen.draw_screen(self.render())
            else:
                time.sleep(0.2) # Display off: skip rendering, save CPU
            time.sleep(0.01)