from hardware.screens.screen import Screen
from PIL import Image
from hardware.state import ScreenState

class AlignmentScreen(Screen):
        
    def setup_input(self):
        self.pipeline.find_target_pixel() #
        self.current_target = self.pipeline.solver.target_pixel

        self.screen_input.controls['A']["press"] = self.select
        self.screen_input.controls['B']["press"] = self.alt_select

        self.screen_input.controls['U']["press"] = self.right
        self.screen_input.controls['D']["press"] = self.left
        self.screen_input.controls['L']["press"] = self.up
        self.screen_input.controls['R']["press"] = self.down

    def left(self):
        if self.current_target is not None:
            # Move the target pixel left
            self.current_target = (self.current_target[0] - 1, self.current_target[1])
            print(f"Target pixel moved left to {self.current_target}")

    def right(self):
        if self.current_target is not None:
            # Move the target pixel right
            self.current_target = (self.current_target[0] + 1, self.current_target[1])
            print(f"Target pixel moved right to {self.current_target}")

    def up(self):
        if self.current_target is not None:
            # Move the target pixel up
            self.current_target = (self.current_target[0], self.current_target[1] - 1)
            print(f"Target pixel moved up to {self.current_target}")

    def down(self):
        if self.current_target is not None:
            # Move the target pixel down
            self.current_target = (self.current_target[0], self.current_target[1] + 1)
            print(f"Target pixel moved down to {self.current_target}")

    def alt_select(self):
        self.ui.change_screen(ScreenState.NAVIGATE)

    def select(self):
        self.pipeline.solver.target_pixel = self.current_target
        print(f"Target pixel selected: {self.current_target}")

    def render(self):
        pipeline = self.pipeline
        current_target = pipeline.solver.target_pixel
        
        if pipeline.latest_image is None:
            return self.renderer.render_many_text(["Waiting for first image..."])
        
        if current_target is None:
            self.pipeline.find_target_pixel() # Find base pixel
            return

        # draw the target pixel on the latest image
        latest_image = pipeline.latest_image
        y, x = current_target
        latest_image.putpixel((x, y), (255, 0, 0))

        return self.renderer.render_image_with_caption(
            latest_image.resize((240, 240), resample=Image.BILINEAR),
            "Alignment"
        )
