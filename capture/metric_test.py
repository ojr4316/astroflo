import matplotlib.pyplot as plt
from ImagingFeedback import ImagingFeedback    
import numpy as np
import os
#from CameraPipeline import CameraPipeline

dir = os.path.dirname(os.path.abspath(__file__))

def main():
    print("Testing Quality Metric Calculation...")
    classifier = ImagingFeedback()
    #cam = CameraPipeline()
    try:
        short = os.path.join(dir, "..", "test_data", "output_0.jpg")
        long = os.path.join(dir, "..", "test_data", "output_30s.jpg")
        dark = os.path.join(dir, "..", "test_data", "image.jpg")
        flat = os.path.join(dir, "..", "test_data", "image_overexposed.jpg")


        test_set = [dark, short, flat, long]
        test_results = ["CapOnRule", "NONE", "OverExposedRule", "NONE"]
        # XAI posthoc explainability with rules

        for i in range(len(test_set)):
            test_image = plt.imread(test_set[i])
        
            if test_image.ndim == 3:
                test_image = np.mean(test_image, axis=2)
            classification, metrics = classifier.classify(test_image)
            if classification != test_results[i]:
                print(f"Test {i} failed: expected {test_results[i]}, got {classification}")
            else:
                print(f"Test {i} passed: {classification}")
            # show image for debugging with matplotlib
            #plt.imshow(test_image, cmap='gray')
            #plt.show()

        #print(f"Metrics: {metrics}")
    except Exception as e:
        print(f"Could not process test image: {e}")

    
if __name__ == "__main__":
    main()