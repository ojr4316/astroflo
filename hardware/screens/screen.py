from abc import ABC, abstractmethod

class Screen(ABC):
    def __init__(self, ui):
        self.ui = ui
        self.renderer = ui.renderer
        self.screen_input = ui.input
        self.pipeline = ui.pipeline

    @abstractmethod
    def render(self):
        pass

    @abstractmethod
    def setup_input(self):
        pass