import os
import time
import io
import argparse
import threading
from enum import Enum
import matplotlib.pyplot as plt
from PIL import Image
from skyfield.api import load

from hardware import ui
from pipeline import Astroflo

from capture.fake_camera import FakeCamera
from solve.astrometry_handler import AstrometryNetSolver
from solve.fake_solver import FakeSolver

from astronomy.telescope import Telescope

from hardware.ui import UIManager, ScreenState

from utils import is_pi

import matplotlib

from operation import OperationManager

if os.name != 'nt':
    matplotlib.use("Agg")
    # For Star Rendering
    # Windows really doesn't like Agg for multi-threading
    # Mac and Linux NEED Agg for multi-threading

def build_camera():
    if is_pi():
        from capture.rpi_camera import RPiCamera
        cam = RPiCamera()
    else:
        img_dir = os.path.dirname(os.path.abspath(__file__))
        file = os.path.normpath(os.path.join(img_dir, "test_data", "bright_sky.jpg"))
        fake_feed = [plt.imread(file)]
        cam = FakeCamera(fake_feed)
        
    return cam

def build_solver():
    if is_pi() and OperationManager.use_real_solver:
        from solve.tetra3 import Tetra3Solver
        return Tetra3Solver()
    else:
        return FakeSolver()

def test_ui(flo: Astroflo, ui: UIManager):
    
    #scope.solve_result(200.98785, 54.7958) # Mizar
   
    #scope.target_manager.set_target(CelestialObject("Alcor", 4.0, "Double", "", 201.31280, 54.9915, "", True))
    #scope.set_position(0.0, 0.0)
    ui.state = ScreenState.NAVIGATE #ui.selected = 27
    #scope.target_manager.catalog = "messier"
    #m45 = scope.target_manager.catalog_loader.search_objects(name="M45")
    #target = scope.observe_local("jupiter")
    #target = m45[0] if m45 else CelestialObject("M45", 0, "Pleiades", "", 56.64, 24.1167, "", False)
    #scope.target_manager.set_target(target)
    

    flo.scope.set_camera_offset(0.0, 0.0)

    ui.render()
    time.sleep(5)
    img = ui.render()
    img.show()

    while True:
        ui.render()
        time.sleep(5)
        img = ui.render()
        img.show()

    #flo.offset_pos_to_brightest_nearby()
    #ui.render()
    #time.sleep(2)
    #img = ui.render()
    #img.show()
    

def running(flo: Astroflo, ui: UIManager):
    #ui.state = ScreenState.NAVIGATE
    if OperationManager.drift:
        drift_render_interval = 0.5
        flo.scope.sky_drift(drift_render_interval)
        time.sleep(drift_render_interval)

def try_set_target(scope: Telescope, name: str):
    target = scope.target_manager.stars.search_by_name(name)
    if len(target) > 0:
        target = target[0]
        scope.target_manager.set_target(target['RAdeg'], target['DEdeg'], target['Name'])
        print(f"Target set to {target['Name']} at RA: {target['RAdeg']}, DEC: {target['DEdeg']}")
    else:
        print(f"Target '{name}' not found in catalog.")

def try_set_planet(scope: Telescope, name: str):
    planet = scope.target_manager.planets.get_current_position(name)
    if planet is not None:
        scope.target_manager.set_target(planet['RAdeg'], planet['DEdeg'], planet['Name'])
        print(f"Target set to {planet['Name']} at RA: {planet['RAdeg']}, DEC: {planet['DEdeg']}")
    else:
        print(f"Planet '{name}' not found in catalog.")

def main():    
    scope = Telescope(
        aperature=200,
        focal_length=1200,
        eyepiece=25,
        eyepiece_fov=40,
    )

    try_set_planet(scope, "Jupiter")
    #try_set_target(scope, "80    UMa")
    solver = build_solver()
    cam = build_camera()

    flo = Astroflo(cam, solver, scope)
    ui = UIManager(flo)
    ui_thread = threading.Thread(target=ui.loop, daemon=True)
    ui_thread.start()
    flo.start()

    if OperationManager.render_test:
        test_ui(flo, ui)
    else:
        try:
            while True:
                running(flo, ui)
        except KeyboardInterrupt:
            flo.stop()
            ui_thread.join()
    
if __name__ == "__main__":
    main()