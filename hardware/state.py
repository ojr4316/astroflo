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