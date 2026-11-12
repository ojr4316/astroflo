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
    IMAGING = 8

class UIState:
    debounce_s = 0.5  # pause after a page change so one press doesn't change pages twice

    def __init__(self):
        self.state = ScreenState.MAIN_MENU
        self.screens = {}
        self.change_input = None # Callback to UI to reset/setup input per page

    def change_screen(self, screen: ScreenState):
        self.state = screen
        self.change_input(screen)
        
        if self.debounce_s:
            time.sleep(self.debounce_s) # prevent multiple page changes

