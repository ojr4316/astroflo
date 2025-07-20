""" State Manager for UI, Controls creating and rendering images, and managing input """
import time
import os
from hardware.renderer import ScreenRenderer
from hardware.input import Input
from hardware.adafruit_tft_bonnet import AdafruitTFTBonnet

from hardware.screens.debug_software import DebugSoftware
from hardware.screens.debug_hardware import DebugHardware
from hardware.screens.main_menu import MainMenu
from hardware.screens.navigation import NavigationScreen
from hardware.screens.directions import DirectionsScreen
from hardware.state import ScreenState

init_text = ['\n', '\n', "~ ASTROFLO ~", "Calibrating camera", "and loading modified", "Tycho catalog.", '\n', '\n', "Please wait 5-10 seconds"]

class UIManager:
    def __init__(self):
        self.pipeline = None
        self.scope = None
        self.state = ScreenState.MAIN_MENU
        self.renderer = ScreenRenderer()
        self.input = Input()
        self.screen = AdafruitTFTBonnet()
        self.screen.set_brightness(0.5)
        self.screen.draw_screen(self.renderer.render_many_text(init_text))

        self.screens = {}

    def init_pipeline(self, pipeline):
        self.pipeline = pipeline
        self.scope = pipeline.scope
        self.build_screens()

    def build_screens(self):
        self.screens = {
            ScreenState.MAIN_MENU: MainMenu(self),
            ScreenState.DEBUG_SOFTWARE: DebugSoftware(self),
            ScreenState.DEBUG_HARDWARE: DebugHardware(self),
            ScreenState.NAVIGATE: NavigationScreen(self),
            ScreenState.DIRECTION: DirectionsScreen(self),
        }

    def change_screen(self, screen: ScreenState):
        self.input.reset()
        self.state = screen
        self.pipeline.configuring = False
        self.screens[self.state].setup_input()
        
        time.sleep(0.5) # prevent multiple page changes

    def render(self):
        match(self.state):
            case ScreenState.MAIN_MENU: return self.screens[ScreenState.MAIN_MENU].render()
            case ScreenState.DEBUG_SOFTWARE: return self.screens[ScreenState.DEBUG_SOFTWARE].render()
            case ScreenState.NAVIGATE: return self.screens[ScreenState.NAVIGATE].render()
            case ScreenState.DEBUG_HARDWARE: return self.screens[ScreenState.DEBUG_HARDWARE].render()
            case ScreenState.DIRECTION: return self.screens[ScreenState.DIRECTION].render()

    def handle_input(self):
        self.screen.handle_input(self.input)

    def loop(self):
        if self.pipeline == None:
            time.sleep(0.25)
            self.loop()
            return
        if os.name == 'nt' or os.uname().nodename != "rpi":
            return
        while True:
            self.screen.draw_screen(self.render())
            time.sleep(0.01)