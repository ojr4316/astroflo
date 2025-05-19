import os
import time
import io
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
    if os.name == "nt" or os.name == "posix":
        img_dir = os.path.dirname(os.path.abspath(__file__))
        file = os.path.normpath(os.path.join(img_dir, "test_data", "test.jpg"))
        fake_feed = [plt.imread(file)]
        cam = FakeCamera(fake_feed)
    else:
        from capture.camera_controllers.RPiCamera import RPiCamera
        cam = RPiCamera()
    return cam

def main():
    solver = AstrometryNetSolver()
    cam = build_camera()

    scope = Telescope(
        aperature=200,
        focal_length=1200,
        eyepiece=25,
        eyepiece_fov=40,
    )

    flo = Astroflo(cam, solver)
    flo.stop()
    start = time.time()
    while flo.latest is None:
        time.sleep(0.1)
    print(f"Time taken to solve: {time.time() - start:.2f} seconds")

    screen = ScreenRenderer()
    result = flo.latest['result']
    ra, dec = result[1]
    scope.set_position(ra, dec)
    t = load.timescale().utc(2024, 1, 17, 22, 0, 0)
    plot = create_telescope_field(scope, t)
    buf = io.BytesIO()
    plot.export(buf, format='png')
    buf.seek(0)
    image = Image.open(buf)
    
    img = screen.render_image_with_caption(image, f"RA: {ra:.4f}              DEC: {dec:.4f}")
    img.show()

def render():
    scope = Telescope(
        aperature=200,
        focal_length=1200,
        eyepiece=25,
        eyepiece_fov=40,
    )

    ui = UIManager(scope)
    ui.loop()

if __name__ == "__main__":
    render()
    #main()