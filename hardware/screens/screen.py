from abc import ABC, abstractmethod

class Screen(ABC):
    def __init__(self, ui):
        self.ui = ui
        self.renderer = ui.renderer
        self.screen_input = ui.screen_input
        self.pipeline = ui.pipeline

        self.selected_y = 0 # Used for menu screens
        self.max_y = 0

        self.selected_x = 0 # Used for menu screens
        self.max_x = 0

        self.input_grow = False
        self.input_speed = 0
        
        self.setup_input()

    @abstractmethod
    def render(self):
        pass

    def setup_input(self):
        self.screen_input.controls['R']["press"] = self.up
        self.screen_input.controls['L']["press"] = self.down

        self.screen_input.controls['R']['release'] = self.release
        self.screen_input.controls['L']['release'] = self.release

        self.screen_input.controls['U']["press"] = self.left
        self.screen_input.controls['D']["press"] = self.right

        self.screen_input.controls['A']["press"] = self.select
        self.screen_input.controls['B']["press"] = self.alt_select

        self.screen_input.controls['C']["press"] = self.debug

    
    def select(self):
        pass

    def alt_select(self):
        pass

    def debug(self):
        pass

    def left(self):
        if self.selected_x > 0:
            self.selected_x -= 1
        else:
            self.selected_x = self.max_x

    def right(self):
        if self.selected_x < self.max_x:
            self.selected_x += 1
        else:
            self.selected_x = 0

    def up(self):
        amount = 1
        if self.input_grow and self.input_speed < 10:
            amount += 1
        if self.selected_y-amount >= 0:
            self.selected_y -= amount
        else:
            self.selected_y = self.max_y

    def down(self):
        amount = 1
        if self.input_grow and self.input_speed < 10:
            amount += 1
        if self.selected_y + amount < self.max_y:
            self.selected_y += amount
        else:
            self.selected_y = 0

    def release(self):
        if self.input_grow:
            self.input_speed = 0