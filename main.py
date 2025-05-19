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

from astronomy.field import create_telescope_field
from astronomy.Telescope import Telescope

from hardware.ui import UIManager

def build_camera():
    if os.uname().nodename == "rpi":
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
    ) # TODO: Save/load telescope and cam prefs to config

    ui = UIManager(scope)
    ui_thread = threading.Thread(target=ui.loop, daemon=True)
    ui_thread.start()

    solver = AstrometryNetSolver()
    cam = build_camera()

    flo = Astroflo(cam, solver)
    
    while True:
        start = time.time()
        while flo.latest is None and (time.time() - start) < 10:
            time.sleep(0.1)
        
        if flo.latest is not None:
            print(f"Time taken to solve: {time.time() - start:.2f} seconds")
            result = flo.latest['result']
            print(result)
            ra, dec = result[1]
            scope.set_position(ra, dec)
    

if __name__ == "__main__":
    main()

#t = load.timescale().utc(2024, 1, 17, 22, 0, 0)


# export plot
#plot = create_telescope_field(scope, t)
#buf = io.BytesIO()
#plot.export(buf, format='png')
#buf.seek(0)
#image = Image.open(buf)
#img = screen.render_image_with_caption(image, f"RA: {ra:.4f}              DEC: {dec:.4f}")