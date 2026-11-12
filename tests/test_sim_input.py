""" Simulated TFT buttons driving the real UI screens """
import threading
import time

import pytest

from hardware.input import Input
from hardware.sim_input import BUTTONS, DisplayButtons, SimInput
from hardware.state import ScreenState


def go(ui, script):
    ui.buttons.run_script(script)
    ui.buttons.drain(ui.screen_input)
    return ui.state_manager.state


# ---------- SimInput on its own ----------
def recorder():
    events = []
    inp = Input()
    for b in BUTTONS:
        inp.controls[b]["press"] = lambda b=b: events.append(("press", b))
        inp.controls[b]["release"] = lambda b=b: events.append(("release", b))
        inp.controls[b]["hold"] = lambda b=b: events.append(("hold", b))
    return inp, events


def test_tap_is_press_then_release():
    inp, events = recorder()
    sim = SimInput()
    sim.tap("a")
    sim.drain(inp)
    assert events == [("press", "A"), ("release", "A")]


def test_hold_reports_hold_while_pressed():
    inp, events = recorder()
    sim = SimInput()
    sim.press("U")
    for _ in range(3):
        sim.step(inp)
    sim.release("U")
    sim.step(inp)
    assert events == [("press", "U"), ("hold", "U"), ("hold", "U"), ("release", "U")]


def test_script_syntax():
    inp, events = recorder()
    sim = SimInput()
    sim.run_script("A +L wait:0.1 -L hold:D:0.2")
    sim.drain(inp)
    assert [e for e in events if e[0] != "hold"] == [("press", "A"), ("release", "A"), ("press", "L"),
                                                    ("release", "L"), ("press", "D"), ("release", "D")]


def test_unknown_button_rejected():
    with pytest.raises(ValueError):
        SimInput().tap("X")


def test_waits_are_honored_by_the_poll_loop():
    inp, events = recorder()
    sim = SimInput()
    sim.run_script("+A wait:0.3 -A")
    start = time.monotonic()
    while sim.pending() or sim.state["A"]:
        sim.read_buttons(inp)
        time.sleep(0.01)
        assert time.monotonic() - start < 2
    assert time.monotonic() - start >= 0.29


def test_display_buttons_delegate_to_display():
    class FakeTFT:
        def read_buttons(self, inp):
            inp.update(True, False, False, False, False, False, False)
    inp, events = recorder()
    DisplayButtons(FakeTFT()).read_buttons(inp)
    assert events == [("press", "A")]


# ---------- navigating the real screens ----------
MENU_ITEMS = [ScreenState.FOCUS, ScreenState.ALIGNMENT, ScreenState.TARGET_LIST, ScreenState.NAVIGATE, ScreenState.IMAGING]


@pytest.mark.parametrize("index,screen", list(enumerate(MENU_ITEMS)))
def test_main_menu_items_and_back(sim_ui, index, screen):
    assert sim_ui.state_manager.state == ScreenState.MAIN_MENU
    assert go(sim_ui, " ".join(["L"] * index + ["A"])) == screen  # L moves down on the rotated screen
    assert go(sim_ui, "B") == ScreenState.MAIN_MENU


def test_menu_wraps_upward(sim_ui):
    assert go(sim_ui, "R A") == ScreenState.IMAGING


def test_info_screen(sim_ui):
    assert go(sim_ui, "B") == ScreenState.INFO
    assert go(sim_ui, "A") == ScreenState.NAVIGATE


def test_pick_target_then_directions(sim_ui):
    assert go(sim_ui, "L L A") == ScreenState.TARGET_LIST
    assert go(sim_ui, "A") == ScreenState.TARGET_SELECT
    assert go(sim_ui, "A") == ScreenState.NAVIGATE
    assert sim_ui.context.target_state.has_target()
    assert go(sim_ui, "A") == ScreenState.DIRECTIONS
    assert go(sim_ui, "B") == ScreenState.NAVIGATE
    assert go(sim_ui, "B") == ScreenState.MAIN_MENU


def test_alignment_select_saves_offset(sim_ui, isolated_files):
    assert go(sim_ui, "L A") == ScreenState.ALIGNMENT
    assert go(sim_ui, "A") == ScreenState.NAVIGATE
    assert (isolated_files / "offset.npy").exists()


def test_imaging_auto_toggle(sim_ui):
    assert go(sim_ui, "R A") == ScreenState.IMAGING
    screen = sim_ui.current_screen()
    before = sim_ui.context.imaging_state.auto_enabled
    screen.selected = type(screen).AUTO
    go(sim_ui, "A")
    assert sim_ui.context.imaging_state.auto_enabled != before


def test_input_thread_processes_events(sim_ui):
    thread = threading.Thread(target=sim_ui.handle_input, daemon=True)
    thread.start()
    sim_ui.buttons.run_script("B")
    for _ in range(200):
        if sim_ui.state_manager.state == ScreenState.INFO:
            break
        time.sleep(0.01)
    sim_ui.stop()
    thread.join(timeout=2)
    assert sim_ui.state_manager.state == ScreenState.INFO
    assert not thread.is_alive()
