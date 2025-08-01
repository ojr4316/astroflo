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
        self.screen.set_brightness(0.5)
        self.screen.draw_screen(render_many_text(init_text))

        self.screen_factory = ScreenFactory()

        self.screens = self.screen_factory.build_screens(self.state_manager, self.screen_input, context, starfield)
        self.state_manager.change_screen(ScreenState.MAIN_MENU) # default to main menu

    def change_input(self, state: ScreenState):
        self.screen_input.reset()
        self.screens[state].setup_input()

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
            self.screen.draw_screen(self.render())
            time.sleep(0.01)