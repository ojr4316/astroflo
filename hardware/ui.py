""" State Manager for UI, Controls creating and rendering images, and managing input """
import time
from enum import Enum
from PIL import Image

from hardware.display import ScreenRenderer
#from hardware.screen import Screen
from hardware.input import Input
from astronomy.Telescope import Telescope

class ScreenState(Enum):
    MAIN_MENU = 0
    CONFIGURE_TELESCOPE = 1
    CONFIGURE_CAMERA = 2
    TARGET_LIST = 3
    TARGET_SELECT = 4
    NAVIGATE = 10

class UIManager:
    def __init__(self, scope: Telescope):
        self.scope = scope
        self.state = ScreenState.MAIN_MENU
        self.renderer = ScreenRenderer()
        self.input = Input()
        #self.screen = Screen()

        self.selected = 0
        self.max_idx = 2

        self.setup_input()

    def setup_input(self):
        self.input.controls['R']["press"] = self.decrease
        self.input.controls['L']["press"] = self.increase

        self.input.controls['U']["press"] = self.left
        self.input.controls['D']["press"] = self.right

        self.input.controls['A']["press"] = self.select

        self.input.controls['C']["press"] = self.alt_select

    def alt_select(self):
        if self.state == ScreenState.NAVIGATE:
            self.state = ScreenState.MAIN_MENU

    def select(self):
        match(self.state):
            case ScreenState.MAIN_MENU: 
                match self.selected:
                    case 0: self.state = ScreenState.CONFIGURE_TELESCOPE
                    case 1: self.state = ScreenState.CONFIGURE_CAMERA
                    case 2: self.state = ScreenState.TARGET_LIST
                    case 3: self.state = ScreenState.NAVIGATE

            case ScreenState.CONFIGURE_TELESCOPE:
                match self.selected:
                    case 0: self.state = ScreenState.MAIN_MENU
            case ScreenState.CONFIGURE_CAMERA:
                match self.selected:
                    case 0: self.state = ScreenState.MAIN_MENU

            case ScreenState.TARGET_SELECT:
                match self.selected:
                    case 0: self.state = ScreenState.MAIN_MENU

            case ScreenState.TARGET_LIST:
                match self.selected:
                    case 0: self.state = ScreenState.MAIN_MENU
                    case 1: self.state = ScreenState.TARGET_SELECT


    def decrease(self):
        if self.selected > 0:
            self.selected -= 1
        else:
            self.selected = self.max_idx

    def increase(self):
        if self.selected < self.max_idx:
            self.selected += 1
        else:
            self.selected = 0

    def left(self):
        if self.state == ScreenState.CONFIGURE_TELESCOPE:
            if self.selected > 0:
                self.scope.modify(self.selected-1)
        if self.state == ScreenState.CONFIGURE_CAMERA:
            if self.selected > 0:
                x, y = self.scope.camera_offset
                match(self.selected):
                    case 1: x -= 0.1
                    case 2: y -= 0.1
                self.scope.camera_offset = (x, y)

    def right(self):
        if self.state == ScreenState.CONFIGURE_TELESCOPE:
            if self.selected > 0:
                self.scope.modify(self.selected-1, True)
        if self.state == ScreenState.CONFIGURE_CAMERA:
            if self.selected > 0:
                x, y = self.scope.camera_offset
                match(self.selected):
                    case 1: x += 0.1
                    case 2: y += 0.1
                self.scope.camera_offset = (x, y)

    def render_main_menu(self):
        title = "~ASTROFLO MENU~"
        options = ["Telescope", "Camera", "Targets", "Navigate"]
        self.max_idx = 3
        return self.renderer.render_menu(title, options, self.selected)
    
    def render_telescope_settings(self):
        self.max_idx = 3
        return self.renderer.render_settings(self.scope.get_settings(), self.selected)

    def render_camera_settings(self):
        self.max_idx = 2
        return self.renderer.render_settings(self.scope.get_cam_settings(), self.selected)

    def render_target_lists(self):
        lists = self.scope.target_manager.catalog_loader.get_catalogs()
        print(lists)
        self.max_idx = len(lists) - 1
        return self.renderer.render_menu("Catalog?", lists, self.selected, True)
    
    def render_target_select(self):
        lists = self.scope.target_manager.get_catalog()
        self.max_idx = len(lists) - 1
        return self.renderer.render_menu("Target?", lists, self.selected, True)

    def render_navigation(self):
        image = Image.new("RGB", (240, 240))

        if self.scope.position is None:
            return self.renderer.render_image_with_caption(image, "N/A")
        
        ra, dec = self.scope.position

        return self.renderer.render_image_with_caption(image, f"RA: {ra:.4f}              DEC: {dec:.4f}")


    def render(self):

        match(self.state):
            case ScreenState.MAIN_MENU: return self.render_main_menu()
            case ScreenState.CONFIGURE_TELESCOPE: return self.render_telescope_settings()
            case ScreenState.CONFIGURE_CAMERA: return self.render_camera_settings()
            case ScreenState.TARGET_LIST: return self.render_target_lists()
            case ScreenState.TARGET_SELECT: return self.render_target_select()

            case ScreenState.NAVIGATE: return self.render_navigation()
            #case ScreenState.TARGET_LIST: return self.

    def loop(self):
        return
        while True:
            self.screen.draw_screen(self.render())
            self.screen.handle_input(self.input)
            time.sleep(0.01)
