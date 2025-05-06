import numpy as np
import cv2
import matplotlib.pyplot as plt
from CameraPipeline import CameraPipeline
from camera_controllers.RPiCamera import RPiCamera

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
    camera_interface = CameraPipeline(RPiCamera())
 
    try:
        images = []
        titles = []
 
        print("\nTaking image with 0.2s exposure...")

        image1 = camera_interface.capture(0.2, 1.0)
        images.append(image1)
        titles.append("0.2s, gain 1.0")
 
        print("\nTaking image with 0.6s exposure...")
        image2 = camera_interface.capture(0.2, 4.0)
        images.append(image2)
        titles.append("0.6s, gain 1.0")
 
        print("\nTaking image with 0.8s exposure...")
        image3 = camera_interface.capture(0.2, 8.0)
        images.append(image3)
        titles.append("0.8s, gain 1.0")
 
        # Calculate image differences for verification
        diff1 = cv2.absdiff(image1, image2)
        mean_diff1 = np.mean(diff1)
        diff2 = cv2.absdiff(image2, image3)
        mean_diff2 = np.mean(diff2)
 
        print(f"Mean difference between images 1 and 2: {mean_diff1:.2f}")
        print(f"Mean difference between images 2 and 3: {mean_diff2:.2f}")
 
        # Display images with histograms for comparison
        try:
            compare_images(images, titles)
        except ImportError:
            print("Matplotlib not available for display")
 
    finally:
        # Clean up
        camera_interface.shutdown()