from hardware.screens.screen import Screen
from PIL import Image, ImageDraw
from hardware.state import ScreenState

class AlignmentScreen(Screen):
        
    def setup_input(self):
        self.screen_input.controls['A']["press"] = self.select
        self.screen_input.controls['B']["press"] = self.alt_select

        self.screen_input.controls['U']["press"] = self.up
        self.screen_input.controls['D']["press"] = self.down
        self.screen_input.controls['L']["press"] = self.right
        self.screen_input.controls['R']["press"] = self.left

    def left(self):
        current_target = self.pipeline.solver.target_pixel
        if current_target is not None:
            # Move the target pixel left
            current_target = (current_target[0] - 1, current_target[1])
            print(f"Target pixel moved left to {current_target}")
            self.pipeline.solver.target_pixel = current_target

    def right(self):
        current_target = self.pipeline.solver.target_pixel
        if current_target is not None:
            # Move the target pixel right
            current_target = (current_target[0] + 1, current_target[1])
            print(f"Target pixel moved right to {current_target}")
            self.pipeline.solver.target_pixel = current_target
    def up(self):
        current_target = self.pipeline.solver.target_pixel
        if current_target is not None:
            # Move the target pixel up
            current_target = (current_target[0], current_target[1] - 1)
            print(f"Target pixel moved up to {current_target}")
            self.pipeline.solver.target_pixel = current_target
    def down(self):
        current_target = self.pipeline.solver.target_pixel
        if current_target is not None:
            # Move the target pixel down
            current_target = (current_target[0], current_target[1] + 1)
            print(f"Target pixel moved down to {current_target}")
            self.pipeline.solver.target_pixel = current_target

    def alt_select(self):
        self.ui.change_screen(ScreenState.MAIN_MENU)

    def select(self):
        self.ui.change_screen(ScreenState.NAVIGATE)
   
    def render(self):
        pipeline = self.pipeline
        current_target = pipeline.solver.target_pixel
        
        if pipeline.latest_image is None:
            return self.renderer.render_many_text(["Waiting for first image..."])
        
        if current_target is None:
            #current_target = (512/2, 512/2) # default center
            current_target = pipeline.find_target_pixel()
            pipeline.solver.target_pixel = current_target

        


        # draw the target pixel on the latest image
        latest_image = Image.fromarray(pipeline.latest_image)
        draw = ImageDraw.Draw(latest_image)
        r = 10
        y, x = current_target[0], current_target[1]
        bbox = [x - r, y - r, x + r, y + r]
        draw.ellipse(bbox, outline="blue", width=3)
        latest_image = latest_image.resize((240, 240))

        return self.renderer.render_image_with_caption(
            latest_image,
            "Alignment"
        )
