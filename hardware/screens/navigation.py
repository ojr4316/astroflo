import time
from hardware.screens.screen import Screen
from PIL import Image

class NavigationScreen(Screen):

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
            if pipeline.target_manager.has_target():
                target = f"|{round(dist, 2)}° from FOV"
            top = f"RA:{ra:.3f}|DEC:{dec:.3f} ({(time.time()-pipeline.latest_timestamp):.1f}s)"
            bot = f"{scope.viewing_angle:.1f}°|{round(1/scope.zoom, 2)}X{target}"
            return self.renderer.render_image_with_caption(image, top, bot)
        except Exception as e:
            print(f"Error rendering navigation: {e}")
            return self.renderer.render_image_with_caption(image, "Error rendering navigation")