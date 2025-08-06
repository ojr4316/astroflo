import os
import time
from PIL import Image
import threading
from observation_context import ObservationContext, CameraState, SolverState, TelescopeState, TargetState
from capture.fake_camera import FakeCamera
from solve.fake_solver import FakeSolver
from hardware.ui import UIManager
from utils import is_pi, BASE_DIR
from astronomy.catalog import Catalog
from astronomy.starfield import StarfieldRenderer
from analyzer import analyzer
import matplotlib
import numpy as np

# For Star Rendering, Windows really doesn't like Agg for multi-threading
if os.name != 'nt':
    matplotlib.use("Agg")
    # Mac and Linux NEED Agg for multi-threading

drift_field = True

def build_camera(camera_state: CameraState):
    if is_pi():
        from capture.rpi_camera import RPiCamera
        return RPiCamera(camera_state)
    else:
        file = os.path.normpath(os.path.join(
            BASE_DIR, "test_data", "out_of_focus.jpg"))
        fake_feed = [np.array(Image.open(file))]
        return FakeCamera(camera_state, fake_feed)

def build_solver(solver_state: SolverState, telescope_state: TelescopeState):
    if is_pi():
        from solve.cedar import CedarSolver
        return CedarSolver(solver_state, telescope_state)
    else:
        return FakeSolver(solver_state, telescope_state)

def try_set_target(catalog: Catalog, target_state: TargetState, name: str):
    target = catalog.search_by_name(name, False)
    if len(target) > 0:
        target = target[0]
        target_state.set_target(target['RAdeg'], target['DEdeg'], target['Name'])
        print(f"Target set to {target['Name']} at RA: {target['RAdeg']}, DEC: {target['DEdeg']}")
    else:
        print(f"Target '{name}' not found in catalog.")

def try_set_planet(catalog: Catalog, target_state: TargetState, name: str):
    planet = catalog.get_current_position(name)
    if planet is not None:
        target_state.set_target(planet['RAdeg'], planet['DEdeg'], planet['Name'])
        print(f"Target set to {planet['Name']} at RA: {planet['RAdeg']}, DEC: {planet['DEdeg']}")
    else:
        print(f"Planet '{name}' not found in catalog.")

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

    #try_set_planet(catalog, ctx.target_state, "Jupiter")
    #ctx.target_state.set_target(213.915416, 19.1822222, "Arcturus")
    starfield = StarfieldRenderer(
        catalog=catalog,
        telescope_state=ctx.telescope_state,
        telescope_optics=ctx.telescope_optics,
        target_state=ctx.target_state
    )

    ui = UIManager(ctx, starfield)

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
