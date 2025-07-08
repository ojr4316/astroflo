""" State Manager for UI, Controls creating and rendering images, and managing input """
import time
import os
import io
from enum import Enum
from PIL import Image
import pytz
import concurrent.futures

from hardware.display import ScreenRenderer
from hardware.input import Input
from hardware.screen import Screen
from pipeline import Astroflo

class ScreenState(Enum):
    MAIN_MENU = 0
    CONFIGURE_TELESCOPE = 1
    CONFIGURE_CAMERA = 2
    TARGET_LIST = 3
    TARGET_SELECT = 4
    DEBUG_SOFTWARE = 5
    DEBUG_HARDWARE = 6
    DEBUG_SOLVE = 7
    NAVIGATE = 10

class UIManager:
    def __init__(self, pipeline: Astroflo):
        self.pipeline = pipeline
        self.scope = pipeline.scope
        self.state = ScreenState.MAIN_MENU
        self.renderer = ScreenRenderer()
        self.input = Input()
        self.screen = Screen()
        self.screen.set_brightness(0.8)

        self.selected = 0
        self.max_idx = 2

        self.setup_input()

    def setup_input(self):
        self.input.controls['R']["press"] = self.decrease
        self.input.controls['L']["press"] = self.increase

        self.input.controls['U']["press"] = self.left
        self.input.controls['D']["press"] = self.right

        self.input.controls['A']["press"] = self.select
        self.input.controls['B']["press"] = self.debug

        self.input.controls['C']["press"] = self.alt_select

    def alt_select(self):
        if self.state == ScreenState.NAVIGATE:
            self.state = ScreenState.MAIN_MENU

    def debug(self):
        if self.state != ScreenState.DEBUG_SOFTWARE:
            self.state = ScreenState.DEBUG_SOFTWARE
        else:
            self.state = ScreenState.NAVIGATE

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
            
            case ScreenState.NAVIGATE:
                self.pipeline.offset_pos_to_brightest_nearby()


    def decrease(self):
        if self.state == ScreenState.NAVIGATE:
            x, y = self.scope.camera_offset
            self.scope.camera_offset = (x - 0.1, y)
            print(f"decreaseing {self.scope.camera_offset}")

        else:
            if self.selected > 0:
                self.selected -= 1
            else:
                self.selected = self.max_idx

    def increase(self):
        if self.state == ScreenState.NAVIGATE:
            #self.scope.viewing_angle += 1
            #if self.scope.viewing_angle > 359:
            #    self.scope.viewing_angle = 0
            #print(self.scope.viewing_angle)
            x, y = self.scope.camera_offset
            self.scope.camera_offset = (x + 0.1, y)
        else:
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
        if self.state == ScreenState.NAVIGATE:
            x, y = self.scope.camera_offset
            self.scope.camera_offset = (x, y - 0.1)

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
        if self.state == ScreenState.NAVIGATE:
            x, y = self.scope.camera_offset
            self.scope.camera_offset = (x, y + 0.1)

    def render_main_menu(self):
        title = "~ASTROFLO MENU~"
        options = ["Telescope", "Camera", "Targets", "Navigate"]
        self.max_idx = 3
        return self.renderer.render_menu(title, options, self.selected)
    
    def render_telescope_settings(self):
        self.max_idx = len(self.scope.settings.get_settings())
        return self.renderer.render_settings(self.scope.settings.get_settings(), self.selected)

    def render_camera_settings(self):
        self.max_idx = len(self.scope.settings.get_cam_settings())
        return self.renderer.render_settings(self.scope.settings.get_cam_settings(), self.selected)

    def render_target_lists(self):
        lists = self.scope.target_manager.catalog_loader.get_catalogs()
        self.max_idx = len(lists) - 1
        return self.renderer.render_menu("Catalog?", lists, self.selected, True)
    
    def render_target_select(self):
        lists = self.scope.target_manager.get_catalog()
        if self.scope.target_manager.catalog == "messier":
            lists = [f"M-{a}" for a in lists]
        self.max_idx = len(lists) - 1
        return self.renderer.render_menu("Target?", lists, self.selected, True)

    def render_navigation(self):
        image = Image.new("RGB", (240, 240))
        if self.scope.position is None:
            return self.renderer.render_image_with_caption(image, "Waiting for first solve...")
        try:
            pos = self.scope.get_position()
            ra, dec = pos[0], pos[1]
            # Actual field rendering is costly, so separate thread
            image, main_target = self.scope.renderer.render()

            return self.renderer.render_image_with_caption(image, f"RA:{ra:.4f} | DEC:{dec:.4f}", main_target if len(main_target) > 0 else "")
        except Exception as e:
            print(f"Error rendering navigation: {e}")
            return self.renderer.render_image_with_caption(image, "Error rendering navigation")


    def render_debug_software(self):
        # get time 
        time = self.scope.get_time()
        location = self.scope.location

        local = pytz.timezone("America/New_York")
        local_time = time.astimezone(local)
        julian_date = time.tt
        utc = time.utc_strftime()

        lst = (time.gast + location.lon.degree / 15.0) % 24.0

        position = self.scope.get_position()

        pos_str = "Unsolved"
        if position:
            pos_str = f"RA:{position[0]:.4f} | DEC:{position[1]:.4f}"

        screen_text = [
            pos_str,
            f"Local: {local_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"UTC: {utc}",
            f"Julian Date: {julian_date:.5f}",
            f"LST: {lst:.2f}h",
            
            f"{location.lat.degree:.4f}°N, {location.lon.degree:.4f}°E",
            f"Viewing Angle: {self.scope.viewing_angle}°",
            f"Lens: {self.scope.eyepiece}mm ({self.scope.eyepiece_fov}° AFOV)",
            f"APT: {self.scope.aperture}mm FL: {self.scope.focal_length}mm",
        ]

        latest_analysis = self.pipeline.analysis.get_latest()
        if latest_analysis is not None:
            lines = str(latest_analysis).replace('"', '').replace("{", "").replace("}", '').split(",")
            screen_text = lines + screen_text
 
        return self.renderer.render_many_text(screen_text)





    def render(self):

        match(self.state):
            case ScreenState.MAIN_MENU: return self.render_main_menu()
            case ScreenState.CONFIGURE_TELESCOPE: return self.render_telescope_settings()
            case ScreenState.CONFIGURE_CAMERA: return self.render_camera_settings()
            case ScreenState.TARGET_LIST: return self.render_target_lists()
            case ScreenState.TARGET_SELECT: return self.render_target_select()
            case ScreenState.DEBUG_SOFTWARE: return self.render_debug_software()
            case ScreenState.NAVIGATE: return self.render_navigation()
            #case ScreenState.TARGET_LIST: return self.

    def loop(self):
        if os.name == 'nt' or os.uname().nodename != "rpi":
            return
        while True:
            self.screen.draw_screen(self.render())
            self.screen.handle_input(self.input)
            time.sleep(0.01)
