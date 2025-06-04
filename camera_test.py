import numpy as np
import cv2
import matplotlib.pyplot as plt
from capture.camera_controllers.FakeCamera import FakeCamera
#from camera_controllers.RPiCamera import RPiCamera

def compare_images(images, titles):    
    n_images = len(images)
    fig, axes = plt.subplots(2, n_images, figsize=(15, 10))
 
    for i, (img, title) in enumerate(zip(images, titles)):
        axes[0, i].imshow(img)
        axes[0, i].set_title(title)
        axes[0, i].axis('off')
 
        for j, color in enumerate(['r', 'g', 'b']):
            hist = cv2.calcHist([img], [j], None, [256], [0, 256])
            axes[1, i].plot(hist, color=color)
 
        axes[1, i].set_title(f"Histogram for {title}")
        axes[1, i].set_xlim([0, 256])
 
    plt.tight_layout()
    plt.show()
 
if __name__ == "__main__":
    camera = FakeCamera()
    camera.start()
 
    images = []
    titles = []

    first = None
    last = None

    print("\nVarying exposure...")
    for i in range(6, 30, 4):
        exposure = float(i) / 10.0
        print(f"Taking image with {exposure:.1f}s exposure...")
        camera.configure(exposure=exposure, gain=16.0)
        last = camera.capture()
        if first is None:
            first = last
        images.append(cv2.imread(last))
        titles.append(f"{i:.1f}s, gain 1.0")

    first = cv2.imread(first)
    last = cv2.imread(last)
    diff = cv2.absdiff(first, last)
    mean_diff = np.mean(diff)
    print(f"Mean difference between first and last images: {mean_diff:.2f}")

    compare_images(images, titles)
    camera.stop()