from abc import ABC, abstractmethod
from typing import ClassVar
from hardware.state import UIState

class Screen(ABC):

    def __init__(self, ui_state: UIState):
        self.ui_state = ui_state

    @abstractmethod
    def setup_input(self):
        pass

    @abstractmethod
    def render(self):
        pass