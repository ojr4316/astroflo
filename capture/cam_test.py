from camera_controllers.FakeCamera import FakeCamera
import matplotlib.pyplot as plt
import os

def main():

    dir = os.path.dirname(os.path.abspath(__file__))
    file = os.path.normpath(os.path.join(dir, "..", "test_data", "test.jpg"))

    fake_feed = [plt.imread(file)]

    cam = FakeCamera(fake_feed)

    try:
        test = cam.capture()
    except Exception as e:
        print(f"Expected could not take image: {e}")
    
    cam.start()

    img = cam.capture()
    plt.imshow(img)
    plt.axis('off')
    plt.title("Random Image")
    plt.show()


if __name__ == "__main__":
    main()