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
from utils import distance_north_east

class ScreenState(Enum):
    MAIN_MENU = 0
    CONFIGURE_TELESCOPE = 1
    CONFIGURE_CAMERA = 2
    TARGET_LIST = 3
    TARGET_SELECT = 4
    DEBUG_SOFTWARE = 5
    DEBUG_HARDWARE = 6
    DEBUG_SOLVE = 7
    DIRECTION = 9
    NAVIGATE = 10

init_text = ['\n', '\n', "~ ASTROFLO ~", "Calibrating camera", "and loading modified", "Tycho catalog.", '\n', '\n', "Please wait 5-10 seconds"]

class UIManager:
    def __init__(self):
        self.pipeline = None
        self.state = ScreenState.MAIN_MENU
        self.renderer = ScreenRenderer()
        self.input = Input()
        self.screen = Screen()
        self.screen.set_brightness(0.3)
        self.screen.draw_screen(self.renderer.render_many_text(init_text))

        self.selected = 0
        self.max_idx = 2

        self.setup_input()

        self.grow = 0
        self.grow_max = 5

    def init_pipeline(self, pipeline):
        self.pipeline = pipeline
        self.scope = pipeline.scope

    def reset_grow(self):
        self.grow = 0

    def setup_input(self):
        self.input.controls['R']["press"] = self.decrease
        self.input.controls['L']["press"] = self.increase

        self.input.controls['R']['release'] = self.reset_grow
        self.input.controls['L']['release'] = self.reset_grow

        self.input.controls['U']["press"] = self.left
        self.input.controls['D']["press"] = self.right

        self.input.controls['A']["press"] = self.select
        self.input.controls['B']["press"] = self.debug

        self.input.controls['C']["press"] = self.alt_select

    def alt_select(self):
        if self.state == ScreenState.NAVIGATE:
            self.state = ScreenState.MAIN_MENU

    def debug(self):
        match(self.state):
            case ScreenState.MAIN_MENU | ScreenState.NAVIGATE:
                self.pipeline.stop_configuring()
                self.state = ScreenState.DEBUG_SOFTWARE
            case ScreenState.DEBUG_SOFTWARE:
                self.pipeline.configuring = True
                self.state = ScreenState.DEBUG_HARDWARE
            case ScreenState.DEBUG_HARDWARE | ScreenState.DIRECTION:
                self.pipeline.stop_configuring()
                self.state = ScreenState.NAVIGATE

    def select(self):
        match(self.state):
            case ScreenState.MAIN_MENU: 
                match self.selected:
                    case 0: self.state = ScreenState.CONFIGURE_TELESCOPE
                    case 1: self.state = ScreenState.DIRECTION
                    case 2: self.state = ScreenState.NAVIGATE

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
            self.grow = -1
        else:
            if self.selected > 0:
                self.selected -= 1
            else:
                self.selected = self.max_idx

    def increase(self):
        if self.state == ScreenState.NAVIGATE:
            self.grow = 1
            #x, y = self.scope.camera_offset
            #self.scope.camera_offset = (x + 0.1, y)
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
            if self.scope.zoom < 10:
                self.scope.zoom += 0.5
            else:
                self.scope.zoom = 10
            

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
            if self.scope.zoom > 0.5:
                self.scope.zoom -= 0.5
            else:
                self.scope.zoom = 0.5
            

    def render_main_menu(self):
        title = "~ASTROFLO MENU~"
        options = ["Target Select", "Directions", "Navigate"]
        self.max_idx = 2
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
            image, dist = self.scope.renderer.render()
            target = ""
            if self.scope.target_manager.has_target():
                target = f"|{round(dist, 2)}° from FOV"
            return self.renderer.render_image_with_caption(image, f"RA:{ra:.3f}|DEC:{dec:.3f} ({(time.time()-self.pipeline.latest_timestamp):.1f}s)", f"{self.scope.viewing_angle:.1f}°|{round(1/self.scope.zoom, 2)}X{target}")
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
            f"{utc}",
            f"Julian Date: {julian_date:.5f}",
            f"LST: {lst:.2f}h",
            
            f"{location.lat.degree:.4f}°N, {location.lon.degree:.4f}°E",
            f"Lens: {self.scope.eyepiece}mm ({self.scope.eyepiece_fov}° AFOV)",
            f"APT: {self.scope.aperture}mm FL: {self.scope.focal_length}mm",
        ]

        if not hasattr(self.pipeline, "analysis"):
            return self.renderer.render_many_text(screen_text)

        latest_analysis = self.pipeline.analysis.get_latest()
        if latest_analysis is not None:
            lines = str(latest_analysis).replace('"', '').replace("{", "").replace("}", '').split(",")
            screen_text = lines + screen_text
 
        return self.renderer.render_many_text(screen_text)

    def render_debug_hardware(self):
        if not self.pipeline.configuring:
            self.pipeline.configuring = True
        if self.pipeline.latest_image is None:
            return self.renderer.render_many_text(["Waiting for first image..."])
        fwhm = self.pipeline.analysis.fwhm_values[-1]  if len(self.pipeline.analysis.fwhm_values) > 0 else 1000
        min_fwhm = min(self.pipeline.analysis.fwhm_values) if self.pipeline.analysis.fwhm_values else 0.0

        return self.renderer.render_image_with_caption(
            self.pipeline.latest_image if self.pipeline.latest_image is not None else Image.new("RGB", (240, 240)),
            f"FWHM: {fwhm:.2f}", f"Min FWHM found: {min_fwhm:.2f}"
        )
    
    def dist_word(self, dist: float):
        dist = abs(dist)
        if dist < 1:
            return "nearby"
        elif dist < 20:
            return "close"
        elif dist < 80:
            return "far"
        else:
            return "distant"

    def render_directions(self):
        if self.scope.position is None:
            return self.renderer.render_many_text(["Waiting for first solve..."])

        if self.scope.target_manager.has_target():
            target_name = self.scope.target_manager.name
            target_ra, target_dec = self.scope.target_manager.get_target_position()
            ra, dec = self.scope.get_position()
            north, east = distance_north_east(ra, dec, target_ra, target_dec, self.scope.viewing_angle)
            north = ("Up" if north >= 0 else "Down") + f" {self.dist_word(north)} ({abs(north):.2f}°)"
            east = ("Right" if east >= 0 else "Left") + f" {self.dist_word(east)} ({abs(east):.2f}°)"

            return self.renderer.render_many_text(['\n', 'CURRENT TARGET:', target_name, '\n', north, '\n', east, '\n', f"Last Solve: {(time.time()-self.pipeline.latest_timestamp):.1f}s"])
        return self.renderer.render_many_text(["No target set."])

    def render(self):
        match(self.state):
            case ScreenState.MAIN_MENU: return self.render_main_menu()
            case ScreenState.CONFIGURE_TELESCOPE: return self.render_telescope_settings()
            case ScreenState.CONFIGURE_CAMERA: return self.render_camera_settings()
            case ScreenState.TARGET_LIST: return self.render_target_lists()
            case ScreenState.TARGET_SELECT: return self.render_target_select()
            case ScreenState.DEBUG_SOFTWARE: return self.render_debug_software()
            case ScreenState.NAVIGATE: return self.render_navigation()
            case ScreenState.DEBUG_HARDWARE: return self.render_debug_hardware()
            case ScreenState.DIRECTION: return self.render_directions()

    def handle_input(self):
        self.screen.handle_input(self.input)

    def loop(self):
        if self.pipeline == None:
            time.sleep(0.2)
            self.loop()
            return
        if os.name == 'nt' or os.uname().nodename != "rpi":
            return
        while True:
            self.screen.draw_screen(self.render())
            self.scope.viewing_angle += self.grow
            if self.scope.viewing_angle > 359:
                self.scope.viewing_angle = 0
            elif self.scope.viewing_angle < 0:
                self.scope.viewing_angle = 359

            time.sleep(0.01)