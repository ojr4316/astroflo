import time
from hardware.screens.screen import Screen
from PIL import Image
from hardware.state import ScreenState

class NavigationScreen(Screen):

    def setup_input(self):
        self.screen_input.controls['A']["press"] = self.select
        self.screen_input.controls['B']["press"] = self.alt_select

        self.screen_input.controls['U']["press"] = self.right
        self.screen_input.controls['D']["press"] = self.left   

    def left(self):
        if self.pipeline.scope.zoom > 1:
            self.pipeline.scope.zoom -= 1
        else:
            self.pipeline.scope.zoom = 0.5

    def right(self):
        if self.pipeline.scope.zoom < 1:
            self.pipeline.scope.zoom = 1
        elif self.pipeline.scope.zoom == 1:
            self.pipeline.scope.zoom = 2
        elif self.pipeline.scope.zoom < 20:
            self.pipeline.scope.zoom += 2
        else:
            self.pipeline.scope.zoom = 20

    def alt_select(self):
        self.ui.change_screen(ScreenState.MAIN_MENU)

    def select(self):
        self.ui.change_screen(ScreenState.DIRECTIONS)

    def render(self):
        pipeline = self.pipeline
        scope = pipeline.scope
        image = Image.new("RGB", (240, 240))
        if scope.position is None:
            return self.renderer.render_image_with_caption(image, "Waiting for first solve...")
        try:
            pos = scope.get_position()
            ra, dec = pos[0], pos[1]
            image, dist = scope.renderer.render()
            target = ""
            if scope.target_manager.has_target():
                target = f"|{round(dist, 2)}° from FOV"
            top = f"RA:{ra:.3f}|DEC:{dec:.3f} ({(time.time()-pipeline.latest_timestamp):.1f}s)"
            bot = f"{scope.viewing_angle:.1f}°|{round(1/scope.zoom, 2)}X{target}"
            return self.renderer.render_image_with_caption(image, top, bot)
        except Exception as e:
            print(f"Error rendering navigation: {e}")
            return self.renderer.render_image_with_caption(image, "Error rendering navigation")