import numpy as np
from abc import ABC, abstractmethod
import cv2
from enum import Enum

class Metric(Enum):
    MEAN = "Mean"
    STDDEV = "StdDev"
    SATURATED = "Saturated"
    SHARPNESS = "Sharpness"
    SNR = "SNR"
    STARCOUNT = "StarCount"

class QualityMetric(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def compute(self, image: np.ndarray) -> float:
        #Compute a quality metric for an image
        pass

class Mean(QualityMetric):
    def __init__(self):
        super().__init__(Metric.MEAN)
    def compute(self, image: np.ndarray) -> float:
        return np.mean(image)
    
class StdDev(QualityMetric):
    def __init__(self):
        super().__init__(Metric.STDDEV)
    def compute(self, image: np.ndarray) -> float:
        return np.std(image)
    
class Saturated(QualityMetric):
    def __init__(self, threshold: float = 0.95):
        super().__init__(Metric.SATURATED)
        self.threshold = threshold
    def compute(self, image: np.ndarray) -> float:
        return np.sum(image > self.threshold) / image.size
    
class Sharpness(QualityMetric):
    def __init__(self):
        super().__init__(Metric.SHARPNESS)
    def compute(self, image: np.ndarray) -> float:
        sobelx = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
        tenengrad = np.sqrt(sobelx**2 + sobely**2)
        focus_measure = np.mean(tenengrad) # More robust
        #laplacian = cv2.Laplacian(image, cv2.CV_64F)
        return focus_measure
    
class SignalToNoiseRatio(QualityMetric):
    def __init__(self):
        super().__init__(Metric.SNR)
    def compute(self, image: np.ndarray) -> float:
        mean = np.mean(image)
        stddev = np.std(image)
        if stddev == 0:
            return 0
        return mean / stddev