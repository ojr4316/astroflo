import matplotlib.pyplot as plt
import os
import time 
from CameraPipeline import CameraPipeline
from camera_controllers.FakeCamera import FakeCamera
#from camera_controllers.RPiCamera import RPiCamera


def main():
    img_dir = os.path.dirname(os.path.abspath(__file__))
    file = os.path.normpath(os.path.join(img_dir, "..", "test_data", "test.jpg"))

    fake_feed = [plt.imread(file)]

    cam = CameraPipeline(FakeCamera(fake_feed))

    cam.start()
    idx = 1
    gain = 1.0
    cam.configure(100_000, gain)
    time.sleep(1)
    img = cam.capture()

    while img is not None:
        plt.imshow(img)
        plt.axis('off')
        plt.title(f"Image {idx}, Gain={gain}")
        plt.show()
        #cam.configure(1_000_000, gain)
        #gain += 0.5
        img = cam.capture()
        idx += 1


if __name__ == "__main__":
    main()