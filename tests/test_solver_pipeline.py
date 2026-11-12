""" Finder frames -> solver -> telescope position, with the fake solver (everywhere) and tetra3 (optional) """
import os
import threading
from queue import Queue

import pytest

import backends
from capture.fake_camera import ImageFolderCamera
from config import Settings
from observation_context import ObservationContext
from solve.fake_solver import FakeSolver, pleiades
from utils import haversine_dist

import numpy as np

TEST_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_data")

# Recorded finder images with the field center they were solved to (tetra3, default database)
RECORDED_FIELDS = {
    "vega_focus.jpg": (280.935, 41.231),  # Lyra, Vega in field
    "test.jpg": (202.731, 52.258),        # Big Dipper handle (Mizar/Alkaid)
    "bright_sky.jpg": (279.636, 8.032),   # Aquila/Serpens
}


def deg_between(a, b):
    return np.degrees(haversine_dist(a[0], a[1], b[0], b[1]))


def test_fake_solver_default_target():
    ctx = ObservationContext()
    solver = FakeSolver(ctx.solver_state, ctx.telescope_state, delay_s=0)
    assert solver.process(np.zeros((4, 4, 3), np.uint8)) == (pleiades, 0.0)
    assert ctx.telescope_state.position == pleiades


def test_fake_solver_target_from_settings():
    ctx = ObservationContext()
    settings = Settings.model_validate({"runtime": {"profile": "sim", "fake_solve_ra": 279.23, "fake_solve_dec": 38.78}})
    solver = backends.build("solver", "fake", ctx, settings)
    solver.delay_s = 0
    solver.process(np.zeros((4, 4, 3), np.uint8))
    assert ctx.telescope_state.position == (279.23, 38.78)


def test_frames_flow_from_camera_to_telescope_position():
    ctx = ObservationContext()
    camera = ImageFolderCamera(ctx.camera_state, TEST_DATA, simulate_exposure=False)
    solver = FakeSolver(ctx.solver_state, ctx.telescope_state, target=(10.0, 20.0), delay_s=0)
    stop = threading.Event()
    thread = threading.Thread(target=solver.solver, args=(camera.queue, stop), daemon=True)
    thread.start()
    camera.running = True
    camera.queue.put(camera.capture())
    for _ in range(100):
        if solver.solves:
            break
        stop.wait(0.02)
    stop.set()
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert solver.solves == 1 and ctx.telescope_state.position == (10.0, 20.0)


def test_failed_solve_keeps_previous_position():
    class NoSolve(FakeSolver):
        def solve(self, image):
            return None
    ctx = ObservationContext()
    ctx.telescope_state.position = (1.0, 2.0)
    NoSolve(ctx.solver_state, ctx.telescope_state).process(np.zeros((2, 2, 3), np.uint8))
    assert ctx.telescope_state.position == (1.0, 2.0)


@pytest.mark.requires_tetra3
@pytest.mark.parametrize("name", sorted(RECORDED_FIELDS))
def test_tetra3_solves_recorded_field(name):
    from solve.tetra3_solver import Tetra3Solver
    ctx = ObservationContext()
    solver = Tetra3Solver(ctx.solver_state, ctx.telescope_state)
    camera = ImageFolderCamera(ctx.camera_state, os.path.join(TEST_DATA, name), simulate_exposure=False)
    camera.running = True
    result = solver.process(camera.capture())
    assert result is not None, f"{name} did not solve"
    assert deg_between(result[0], RECORDED_FIELDS[name]) < 1.0


@pytest.mark.requires_tetra3
def test_tetra3_vega_field_contains_vega():
    from solve.tetra3_solver import Tetra3Solver
    ctx = ObservationContext()
    camera = ImageFolderCamera(ctx.camera_state, os.path.join(TEST_DATA, "vega_focus.jpg"), simulate_exposure=False)
    camera.running = True
    coords, _ = Tetra3Solver(ctx.solver_state, ctx.telescope_state).solve(camera.capture())
    assert deg_between(coords, (279.234, 38.784)) < 8  # inside the ~17 deg field


@pytest.mark.requires_tetra3
def test_tetra3_noise_does_not_solve():
    from solve.tetra3_solver import Tetra3Solver
    ctx = ObservationContext()
    noise = np.random.randint(0, 30, (256, 256, 3), dtype=np.uint8)
    assert Tetra3Solver(ctx.solver_state, ctx.telescope_state).solve(noise) is None
