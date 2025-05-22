from feedback_classifier.metrics.QualityMetric import QualityMetric, Metric
from photutils.detection import DAOStarFinder
import numpy as np

class StarCount(QualityMetric):
    def __init__(self, threshold: float = 5, fwhm: float = 3.0):
        super().__init__(Metric.STARCOUNT)
        self.threshold = threshold  
        
    
    def compute(self, image: np.ndarray) -> float:
        std_dev = np.std(image)
        self.finder = DAOStarFinder(threshold=1.*std_dev, fwhm=3.0)
        stars = self.finder(image)
        if stars is None:
            return 0
        print(len(stars))
        return len(stars)