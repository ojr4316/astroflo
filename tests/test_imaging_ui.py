from PIL import Image

from hardware import renderer
from hardware.input import Input
from hardware.state import UIState, ScreenState
from hardware.screens.imaging import ImagingScreen
from hardware.screens.main_menu import MainMenu
from observation_context import ImagingState, TargetState

DOT_CENTER = (renderer.WIDTH - renderer.STATUS_DOT_MARGIN - renderer.STATUS_DOT_RADIUS,
              renderer.STATUS_DOT_MARGIN + renderer.STATUS_DOT_RADIUS)


def dot_color(connected):
    renderer.status_provider = lambda: connected
    img = Image.new("RGB", (renderer.WIDTH, renderer.HEIGHT))
    renderer.draw_status_dot(img)
    return img.getpixel(DOT_CENTER)


def test_status_dot_colors():
    try:
        assert dot_color(True) == renderer.COLOR_STATUS_OK
        assert dot_color(False) == renderer.COLOR_STATUS_BAD
    finally:
        renderer.status_provider = None


def test_status_dot_on_rendered_screen():
    renderer.status_provider = lambda: True
    try:
        out = renderer.render_many_text(["hello"])
        # _transform rotates -90 (clockwise): logical top-right -> physical bottom-right
        px = out.getpixel((renderer.WIDTH - 1 - DOT_CENTER[1], DOT_CENTER[0]))
        assert px == renderer.COLOR_STATUS_OK
    finally:
        renderer.status_provider = None


STRIP_PX = (2, renderer.HEIGHT - 2)  # logical bottom-left, inside the strip, clear of the text


def strip_pixel(provider):
    renderer.feedback_provider = provider
    try:
        img = Image.new("RGB", (renderer.WIDTH, renderer.HEIGHT))
        renderer.draw_feedback_strip(img)
        return img.getpixel(STRIP_PX)
    finally:
        renderer.feedback_provider = None


def test_feedback_strip():
    from feedback.image_feedback import FeedbackResult, OK
    warn = FeedbackResult("blurred", "Out of focus", "warning")
    err = FeedbackResult("cap_on", "Lens cap on?", "error")
    assert strip_pixel(lambda: warn) == renderer.COLOR_FEEDBACK_WARNING
    assert strip_pixel(lambda: err) == renderer.COLOR_FEEDBACK_ERROR
    assert strip_pixel(lambda: OK) == renderer.COLOR_BLACK

    def boom():
        raise RuntimeError("analyzer gone")
    assert strip_pixel(boom) == renderer.COLOR_BLACK


def test_feedback_strip_on_rendered_screen():
    from feedback.image_feedback import FeedbackResult
    renderer.feedback_provider = lambda: FeedbackResult("cap_on", "Lens cap on?", "error")
    try:
        out = renderer.render_many_text(["hello"])
        # rotate -90 (clockwise): logical (x, y) -> physical (HEIGHT - 1 - y, x)
        assert out.getpixel((renderer.HEIGHT - 1 - STRIP_PX[1], STRIP_PX[0])) == renderer.COLOR_FEEDBACK_ERROR
    finally:
        renderer.feedback_provider = None


class FakeUIState(UIState):
    def change_screen(self, screen):
        self.state = screen


def make_screen():
    ui = FakeUIState()
    imaging = ImagingState()
    screen = ImagingScreen(ui, Input(), imaging, TargetState())
    return ui, imaging, screen


def test_auto_toggle_and_capture():
    ui, imaging, screen = make_screen()
    screen.selected = ImagingScreen.AUTO
    screen.select()
    assert imaging.auto_enabled
    screen.select()
    assert not imaging.auto_enabled

    screen.selected = ImagingScreen.CAPTURE
    screen.select()
    assert imaging.manual_requested.is_set()


def test_back_keeps_auto_setting():
    ui, imaging, screen = make_screen()
    imaging.auto_enabled = True
    screen.back()
    assert ui.state == ScreenState.MAIN_MENU and imaging.auto_enabled


def test_imaging_screen_renders():
    _, imaging, screen = make_screen()
    imaging.set_result("Saved")
    assert "Saved" in screen.status_lines()
    assert screen.render().size == (renderer.WIDTH, renderer.HEIGHT)


def test_main_menu_routes_to_imaging():
    ui = FakeUIState()
    menu = MainMenu(ui, Input())
    menu.selected_y = menu.options.index("Imaging")
    menu.select()
    assert ui.state == ScreenState.IMAGING
