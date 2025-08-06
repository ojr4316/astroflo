from hardware.screens.screen import Screen
from PIL import Image, ImageDraw
from hardware.state import ScreenState
from observation_context import SolverState, CameraState
from hardware.renderer import render_image_with_caption, render_many_text
from analyzer import analyzer

class AlignmentScreen(Screen):
    
    def __init__(self, ui_state, screen_input, camera_state: CameraState, solver_state: SolverState):
        super().__init__(ui_state, screen_input)
        self.camera_state = camera_state
        self.solver_state = solver_state

    def setup_input(self):
        # Acquire current target pixel from context
        self.current_target = self.solver_state.target_pixel

        self.screen_input.controls['A']["press"] = self.select
        self.screen_input.controls['B']["press"] = self.alt_select

        self.screen_input.controls['U']["hold"] = self.up
        self.screen_input.controls['D']["hold"] = self.down
        self.screen_input.controls['L']["hold"] = self.right
        self.screen_input.controls['R']["hold"] = self.left

    def left(self):
        current_target = self.current_target
        if current_target is not None:
            # Move the target pixel left
            self.current_target = (current_target[0] - 1, current_target[1])
            print(f"Target pixel moved left to {current_target}")

    def right(self):
        current_target = self.current_target
        if current_target is not None:
            # Move the target pixel right
            self.current_target = (current_target[0] + 1, current_target[1])
            print(f"Target pixel moved right to {current_target}")

    def up(self):
        current_target = self.current_target
        if current_target is not None:
            # Move the target pixel up
            self.current_target = (current_target[0], current_target[1] - 1)
            print(f"Target pixel moved up to {current_target}")
            
    def down(self):
        current_target = self.current_target
        if current_target is not None:
            # Move the target pixel down
            self.current_target = (current_target[0], current_target[1] + 1)
            print(f"Target pixel moved down to {current_target}")

    def alt_select(self):
        self.ui_state.change_screen(ScreenState.MAIN_MENU)

    def select(self):
        self.solver_state.save_offset(self.current_target)
        print(f"Target pixel set to {self.current_target}")
        self.ui_state.change_screen(ScreenState.NAVIGATE)
   
    def render(self):
        current_target = self.current_target

        if self.camera_state.latest_image is None:
            return render_many_text(["Waiting for first image..."])
        
        if current_target is None:
            #current_target = (512/2, 512/2) # default center
            pixel, value = analyzer.find_brightest(self.camera_state.latest_image)
            self.current_target = pixel
            return

        # draw target on the latest image
        latest_image = Image.fromarray(self.camera_state.latest_image)
        draw = ImageDraw.Draw(latest_image)
        r = 10
        y, x = current_target[0], current_target[1]
        bbox = [x - r, y - r, x + r, y + r]
        draw.ellipse(bbox, outline="blue", width=3)
        latest_image = latest_image.resize((240, 240))

        return render_image_with_caption(
            latest_image,
            "Alignment"
        )
