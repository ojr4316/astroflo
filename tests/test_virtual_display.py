""" Headless virtual display and the UI render loop """
import threading
import time

from PIL import Image

from hardware.virtual_display import VirtualDisplay


def test_frame_is_240_square():
    d = VirtualDisplay()
    d.draw_screen(Image.new("RGB", (100, 50), (255, 0, 0)))
    frame = d.get_frame()
    assert frame.size == (240, 240) and frame.mode == "RGB"


def test_brightness_dims_frame():
    d = VirtualDisplay()
    d.set_brightness(1.0)
    d.draw_screen(Image.new("RGB", (240, 240), (200, 200, 200)))
    full = d.get_frame().getpixel((5, 5))[0]
    d.set_brightness(0.25)
    d.draw_screen(Image.new("RGB", (240, 240), (200, 200, 200)))
    assert d.get_frame().getpixel((5, 5))[0] < full


def test_none_frame_ignored_and_clear_blacks_out():
    d = VirtualDisplay()
    d.draw_screen(None)
    assert d.get_frame() is None and d.frame_count == 0
    d.clear()
    assert d.get_frame().getpixel((0, 0)) == (0, 0, 0)


def test_snapshots_written_and_throttled(tmp_path):
    d = VirtualDisplay(snapshot_dir=str(tmp_path / "snaps"), snapshot_interval_s=60)
    for _ in range(5):
        d.draw_screen(Image.new("RGB", (240, 240)))
    files = list((tmp_path / "snaps").glob("*.png"))
    assert len(files) == 1 and Image.open(files[0]).size == (240, 240)


def test_ui_loop_renders_to_virtual_display(sim_ui):
    thread = threading.Thread(target=sim_ui.draw_screen, daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while sim_ui.screen.frame_count < 3 and time.monotonic() < deadline:
        time.sleep(0.02)
    sim_ui.stop()
    thread.join(timeout=2)
    assert sim_ui.screen.frame_count >= 3
    assert sim_ui.screen.get_frame().size == (240, 240)
    assert sim_ui.screen.snapshots_written >= 1
    assert not thread.is_alive()


def test_display_off_stops_rendering(sim_ui):
    sim_ui.set_display(enabled=False)
    count = sim_ui.screen.frame_count
    sim_ui.draw_once()
    assert sim_ui.screen.frame_count == count
    sim_ui.set_display(enabled=True)
    sim_ui.draw_once()
    assert sim_ui.screen.frame_count == count + 1
