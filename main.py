import os
import time
from PIL import Image
import threading
from observation_context import ObservationContext, CameraState, SolverState, TelescopeState
from capture.fake_camera import FakeCamera
from solve.fake_solver import FakeSolver
from hardware.state import UIState
from hardware.ui import UIManager
from utils import is_pi, BASE_DIR
from astronomy.catalog import Catalog
from astronomy.starfield import StarfieldRenderer
from analyzer import analyzer

drift_field = True

def build_camera(camera_state: CameraState):
    if is_pi():
        from capture.rpi_camera import RPiCamera
        return RPiCamera(camera_state)
    else:
        file = os.path.normpath(os.path.join(
            BASE_DIR, "test_data", "out_of_focus.jpg"))
        fake_feed = [Image.open(file)]
        return FakeCamera(camera_state, fake_feed)

def build_solver(solver_state: SolverState, telescope_state: TelescopeState):
    if is_pi():
        from solve.tetra3 import Tetra3Solver
        return Tetra3Solver(solver_state, telescope_state)
    else:
        return FakeSolver(solver_state, telescope_state)

last_time = None
def running(telescope_state: TelescopeState):
    global last_time
    now = time.perf_counter()
    delta = now - last_time if last_time is not None else 0
    last_time = now
    last_time = time.perf_counter()
    if drift_field:
        telescope_state.sky_drift(delta)
        time.sleep(delta)
    time.sleep(0.01)

def main():
    ctx = ObservationContext()
    catalog = Catalog(ctx.environment)
    state = UIState()

    starfield = StarfieldRenderer(
        catalog=catalog,
        telescope_state=ctx.telescope_state,
        telescope_optics=ctx.telescope_optics,
        target_state=ctx.target_state
    )

    ui = UIManager(state, ctx, starfield)

    camera = build_camera(ctx.camera_state)
    solver = build_solver(ctx.solver_state, ctx.telescope_state)

    capture_thread = threading.Thread(target=camera.capturer)
    capture_thread.start()

    solver_thread = threading.Thread(
        target=solver.solver, args=(camera.queue,))
    solver_thread.start()

    ui_thread = threading.Thread(target=ui.draw_screen)
    ui_thread.start()

    input_thread = threading.Thread(target=ui.handle_input)
    input_thread.start()

    analyzer_thread = threading.Thread(target=analyzer.process)
    analyzer_thread.start()

    ctx.telescope_state.stel.run_server()

    try:
        while True:
            running(ctx.telescope_state)
    except KeyboardInterrupt:
        ui_thread.join()

if __name__ == "__main__":
    main()
