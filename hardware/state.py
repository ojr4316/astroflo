import time
from enum import Enum

class ScreenState(Enum):
    MAIN_MENU = 0
    ALIGNMENT = 1
    FOCUS = 2
    TARGET_SELECT = 3
    TARGET_LIST = 4
    DIRECTIONS = 5
    NAVIGATE = 6
    INFO = 7

class UIState:
    def __init__(self):
        self.screen = ScreenState.MAIN_MENU
        self.screens = {}

    def change_screen(self, screen: ScreenState):
        self.input.reset()
        self.state = screen
        self.screens[self.state].setup_input()
        time.sleep(0.5) # prevent multiple page changes

