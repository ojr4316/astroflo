import time
from hardware.screens.screen import Screen
from PIL import Image
from hardware.state import ScreenState
from hardware.renderer import render_image_with_caption, render_many_text
from observation_context import TelescopeState, TelescopeOptics, TargetState, SolverState
from astronomy.starfield import StarfieldRenderer

class NavigationScreen(Screen):

    def __init__(self, ui_state, screen_input, telescope_state: TelescopeState, telescope_optics: TelescopeOptics, target_state: TargetState, solver_state: SolverState, starfield_renderer: StarfieldRenderer):
        super().__init__(ui_state, screen_input)
        self.ui_state = ui_state
        self.telescope_state = telescope_state
        self.telescope_optics = telescope_optics
        self.target_state = target_state
        self.solver_state = solver_state
        self.starfield_renderer = starfield_renderer

    def setup_input(self):
        self.screen_input.controls['A']["press"] = self.select
        self.screen_input.controls['B']["press"] = self.alt_select

        self.screen_input.controls['U']["press"] = self.right
        self.screen_input.controls['D']["press"] = self.left   

    def left(self):
        if self.telescope_optics.zoom > 1:
            self.telescope_optics.zoom -= 1
        else:
            self.telescope_optics.zoom = 0.5

    def right(self):
        if self.telescope_optics.zoom < 1:
            self.telescope_optics.zoom = 1
        elif self.telescope_optics.zoom == 1:
            self.telescope_optics.zoom = 2
        elif self.telescope_optics.zoom < 20:
            self.telescope_optics.zoom += 2
        else:
            self.telescope_optics.zoom = 20

    def alt_select(self):
        self.ui_state.change_screen(ScreenState.MAIN_MENU)

    def select(self):
        self.ui_state.change_screen(ScreenState.DIRECTIONS)

    def render(self):
        image = Image.new("RGB", (240, 240))
        if self.telescope_state.position is None:
            return render_image_with_caption(image, "Waiting for first solve...")
        try:
            pos = self.telescope_state.position
            ra, dec = pos[0], pos[1]
            image, dist = self.starfield_renderer.render()
            target = ""
            if self.target_state.has_target():
                target = f"|{round(dist, 2)}° from FOV"
            top = f"RA:{ra:.3f}|DEC:{dec:.3f} ({(time.time()-self.solver_state.last_solved):.1f}s)"
            bot = f"{self.telescope_state.roll:.1f}°|{round(1/self.telescope_optics.zoom, 2)}X{target}"
            
            return render_image_with_caption(image, top, bot)
        except Exception as e:
            print(f"Error rendering navigation: {e}")
            return render_image_with_caption(image, "Error rendering navigation")