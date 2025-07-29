from abc import ABC, abstractmethod
from hardware.input import Input
from hardware.state import UIState

class Screen(ABC):

    def __init__(self, ui_state: UIState, screen_input: Input):
        self.ui_state = ui_state
        self.screen_input = screen_input

    @abstractmethod
    def setup_input(self):
        pass

    @abstractmethod
    def render(self):
        pass