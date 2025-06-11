import os
import time
import io
import argparse
import threading
from enum import Enum
import matplotlib.pyplot as plt
from PIL import Image
from skyfield.api import load

from Astroflo import Astroflo

from capture.FakeCamera import FakeCamera
from solve.astrometry_handler import AstrometryNetSolver
#from solve.tetra3 import Tetra3Solver

from astronomy.Telescope import Telescope
from astronomy.celestial import CelestialObject

from hardware.ui import UIManager, ScreenState

from utils import is_pi

from astronomy.field import enhance_telescope_field

import matplotlib
matplotlib.use("Agg")

def build_camera():
    if is_pi():
        from capture.RPiCamera import RPiCamera
        cam = RPiCamera()
    else:
        img_dir = os.path.dirname(os.path.abspath(__file__))
        file = os.path.normpath(os.path.join(img_dir, "test_data", "bright_sky.jpg"))
        fake_feed = [plt.imread(file)]
        cam = FakeCamera(fake_feed)
        
    return cam

class OperationMode(Enum):
    MANUAL = 0
    AUTO = 1
    TEST_UI = 2

def main(operation_mode: OperationMode = OperationMode.AUTO):
    scope = Telescope(
        aperature=200,
        focal_length=1200,
        eyepiece=25,
        eyepiece_fov=40,
    )

    ui = UIManager(scope)
    ui_thread = threading.Thread(target=ui.loop, daemon=True)
    ui_thread.start()

    solver = AstrometryNetSolver()
    cam = build_camera()

    flo = Astroflo(cam, solver, scope)
    flo.start()

    time.sleep(1)
    match operation_mode:
        case OperationMode.MANUAL:
            pass
        case OperationMode.AUTO:
            ui.state = ScreenState.NAVIGATE
            try:
                while True:
                    time.sleep(1)
                    # Check subsystems and restart if necessary
            except Exception as e:
                print(e)
                flo.stop()
                ui_thread.join()
        case OperationMode.TEST_UI:

            #scope.set_position(279.6348, 8.0315)
            scope.set_position(200.98785, 54.7958) # Mizar
            scope.set_camera_offset(2.0, 0.0)
            scope.target_manager.set_target(CelestialObject("Alcor", 4.0, "Double", "", 201.31280, 54.9915, "", True))
            print(scope.target_manager.target)
            #scope.set_position(0.0, 0.0)
            ui.state = ScreenState.NAVIGATE #ui.selected = 27
            #scope.target_manager.catalog = "messier"
            #m45 = scope.target_manager.catalog_loader.search_objects(name="M45")
            #target = scope.observe_local("jupiter")
            #target = m45[0] if m45 else CelestialObject("M45", 0, "Pleiades", "", 56.64, 24.1167, "", False)
            #scope.set_position(target.ra, target.dec)
            #scope.target_manager.set_target(target)
            
            #scope.set_camera_offset(0.0, 0.0)
            ui.render()
            time.sleep(1)
            img = ui.render()
            img.show()

    
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Astroflo Telescope Control")
    parser.add_argument("--ui", action="store_true", help="Run in test mode manually rendering single UI frame")

    args = parser.parse_args()
    
    test_ui = args.ui
    if test_ui:
        main(OperationMode.TEST_UI)
    else:
        main(OperationMode.AUTO)