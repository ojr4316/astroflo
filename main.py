import os
import time
import io
import threading
import matplotlib.pyplot as plt
from PIL import Image
from skyfield.api import load

from Astroflo import Astroflo

from capture.FakeCamera import FakeCamera
from solve.astrometry_handler import AstrometryNetSolver

from astronomy.Telescope import Telescope
from astronomy.celestial import CelestialObject

from hardware.ui import UIManager, ScreenState

def build_camera():
    if os.name != 'nt' and os.uname().nodename == "rpi":
        from capture.RPiCamera import RPiCamera
        cam = RPiCamera()
    else:
        img_dir = os.path.dirname(os.path.abspath(__file__))
        file = os.path.normpath(os.path.join(img_dir, "test_data", "test.jpg"))
        fake_feed = [plt.imread(file)]
        cam = FakeCamera(fake_feed)
        
    return cam

def main():
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

    time.sleep(10)

    ui.state = ScreenState.NAVIGATE

    #m45 = CelestialObject("M45", 0, "Pleiades", "", 56.64, 24.1167, "", False)
    #scope.set_position(m45.ra, m45.dec)

    target = scope.observe_local("jupiter")
    scope.set_camera_offset(0.0, 0.0)

    #scope.set_position(target.ra, target.dec)
    scope.target_manager.set_target(target)

    start = time.time()
    img = ui.render()
    end = time.time()
    print(f"Render time: {end - start:.2f} seconds")
    img.show()

    #time.sleep(5)
    #ui.selected = 27
    #scope.target_manager.catalog = "messier"
    
    
if __name__ == "__main__":
    main()