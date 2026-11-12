""" Every UI screen renders a 240x240 frame with simulated state, solved and unsolved """
import numpy as np
import pytest
from PIL import Image

from hardware.state import ScreenState


def prepare(ui, solved: bool):
    ctx = ui.context
    ctx.camera_state.latest_image = np.random.randint(0, 255, (120, 160, 3), dtype=np.uint8)
    if solved:
        ctx.telescope_state.solve_result((279.23, 38.78), 10.0)  # Vega
        ctx.target_state.set_target(283.39, 33.03, "M57")


@pytest.mark.parametrize("solved", [False, True], ids=["unsolved", "solved"])
@pytest.mark.parametrize("state", list(ScreenState), ids=lambda s: s.name)
def test_screen_renders(sim_ui, state, solved):
    prepare(sim_ui, solved)
    sim_ui.set_screen(state)
    img = sim_ui.render()
    assert isinstance(img, Image.Image) and img.size == (240, 240)
    sim_ui.draw_once()
    assert sim_ui.screen.get_frame().size == (240, 240)
