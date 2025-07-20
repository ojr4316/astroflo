from enum import Enum

class ScreenState(Enum):
    MAIN_MENU = 0
    DEBUG_SOFTWARE = 1
    DEBUG_HARDWARE = 2
    TARGET_SELECT = 3
    TARGET_LIST = 4
    DIRECTION = 5
    NAVIGATE = 6