import os
import time
import threading
import matplotlib
import matplotlib.pyplot as plt
from pipeline import Astroflo
from hardware.ui import UIManager, ScreenState
from astronomy.telescope import Telescope
from operation import OperationManager
from capture.fake_camera import FakeCamera
from solve.fake_solver import FakeSolver
from utils import is_pi
from astronomy.target import TargetManager
from astronomy.renderer import NavigationStarfield
from astronomy.telescope_state import TelescopeState


from observation_context import ObservationContext

# For Star Rendering, Windows really doesn't like Agg for multi-threading
if os.name != 'nt':
    matplotlib.use("Agg")
    # Mac and Linux NEED Agg for multi-threading
    
def test_ui(flo: Astroflo, ui: UIManager):
    ui.render()
    time.sleep(5)
    img = ui.render()
    img.show()

    while True:
        ui.render()
        time.sleep(4)
        img = ui.render()
        img.show()
        time.sleep(4)
    
last_time = None
def running(flo: Astroflo):
    global last_time
    now = time.perf_counter()
    delta = now - last_time if last_time is not None else 0
    last_time = now
    last_time = time.perf_counter()
    if OperationManager.drift:
        flo.scope.sky_drift(delta)
        time.sleep(delta)
    time.sleep(0.01)

def handle_input(ui: UIManager):
    while True:
        ui.handle_input()
        time.sleep(0.01)

def try_set_target(scope: Telescope, name: str):
    target = scope.target_manager.stars.search_by_name(name)
    if len(target) > 0:
        target = target[0]
        scope.target_manager.set_target(target['RAdeg'], target['DEdeg'], target['Name'])
        print(f"Target set to {target['Name']} at RA: {target['RAdeg']}, DEC: {target['DEdeg']}")
    else:
        print(f"Target '{name}' not found in catalog.")

def try_set_planet(scope: Telescope, name: str):
    planet = scope.target_manager.ephemeris.get_current_position(name)
    if planet is not None:
        scope.target_manager.set_target(planet['RAdeg'], planet['DEdeg'], planet['Name'])
        print(f"Target set to {planet['Name']} at RA: {planet['RAdeg']}, DEC: {planet['DEdeg']}")
    else:
        print(f"Planet '{name}' not found in catalog.")

def main():    
    ui = UIManager()
    scope = Telescope(
        aperture=200,
        focal_length=1200,
        eyepiece=25,
        eyepiece_fov=40,
    )
    





    #try_set_planet(scope, "Uranus")
    try_set_target(scope, "Deneb")
    solver = build_solver()
    cam = build_camera()

    flo = Astroflo(cam, solver, scope)
    ui_thread = threading.Thread(target=ui.loop, daemon=True)
    ui_thread.start()
    input_thread = threading.Thread(target=handle_input, args=[ui], daemon=True)
    input_thread.start()
    flo.start()

    ui.init_pipeline(flo)
    ui.change_screen(ScreenState.MAIN_MENU)

    if OperationManager.render_test:
        test_ui(flo, ui)
    else:
        try:
            while True:
                running(flo)
        except KeyboardInterrupt:
            flo.stop()
            ui_thread.join()
    
if __name__ == "__main__":
    main()