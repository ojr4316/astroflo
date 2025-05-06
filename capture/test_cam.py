from camera_controllers.FakeCamera import FakeCamera
import matplotlib.pyplot as plt
import os

def main():
    img_dir = os.path.dirname(os.path.abspath(__file__))
    file = os.path.normpath(os.path.join(img_dir, "..", "test_data", "test.jpg"))

    fake_feed = [plt.imread(file)]

    cam = FakeCamera(fake_feed)

    cam.start()
    img = cam.capture()
    idx = 1

    while img is not None:
        plt.imshow(img)
        plt.axis('off')
        plt.title(f"Image {idx}")
        plt.show()
        img = cam.capture()
        idx += 1


if __name__ == "__main__":
    main()