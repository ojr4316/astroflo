import os
import time
import matplotlib.pyplot as plt

from Astroflo import Astroflo

from capture.camera_controllers.FakeCamera import FakeCamera
from solve.solvers.astrometry_handler import AstrometryNetSolver

if os.name != "nt":
    from capture.camera_controllers.RPiCamera import RPiCamera

def main():
    solver = AstrometryNetSolver()
    if os.name == "nt":
        img_dir = os.path.dirname(os.path.abspath(__file__))
        file = os.path.normpath(os.path.join(img_dir, "test_data", "test.jpg"))

        fake_feed = [plt.imread(file)]
        cam = FakeCamera(fake_feed)
    else:
        cam = RPiCamera()

    flo = Astroflo(cam, solver)
    flo.stop()
    time.sleep(10)
    print(flo.latest)
    




if __name__ == "__main__":
    main()