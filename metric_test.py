import matplotlib.pyplot as plt
from feedback_classifier.ImagingFeedback import ImagingFeedback    
import numpy as np
import os
# TODO: Investigate XAI posthoc explainability with rules

image_dir = os.path.dirname(os.path.abspath(__file__))
classifier = ImagingFeedback()

def test_cap():
    test_image = plt.imread(os.path.join(image_dir, "test_data", "image.jpg"))
    if test_image.ndim == 3:
        test_image = np.mean(test_image, axis=2)
    classification, metrics = classifier.classify(test_image)
    assert classification == "CapOnRule", f"Expected 'CapOnRule', got {classification}"

def test_overexposed():
    test_image = plt.imread(os.path.join(image_dir, "test_data", "image_overexposed.jpg"))
    if test_image.ndim == 3:
        test_image = np.mean(test_image, axis=2)
    classification, metrics = classifier.classify(test_image)
    assert classification == "OverExposedRule", f"Expected 'OverExposedRule', got {classification}"

def test_no_classification():
    test_image = plt.imread(os.path.join(image_dir, "test_data", "output_0.jpg"))
    if test_image.ndim == 3:
        test_image = np.mean(test_image, axis=2)
    classification, metrics = classifier.classify(test_image)
    assert classification == "NONE", f"Expected 'NONE', got {classification}"

    test_image = plt.imread(os.path.join(image_dir, "test_data", "output_30s.jpg"))
    if test_image.ndim == 3:
        test_image = np.mean(test_image, axis=2)
    classification, metrics = classifier.classify(test_image)
    assert classification == "NONE", f"Expected 'NONE', got {classification}"