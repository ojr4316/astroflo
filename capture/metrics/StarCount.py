from metrics.QualityMetric import QualityMetric, Metric
from photutils.detection import DAOStarFinder
import numpy as np

class StarCount(QualityMetric):
    def __init__(self, threshold: float = 0.2, fwhm: float = 3.0):
        super().__init__(Metric.STARCOUNT)
        self.threshold = threshold  
        
        self.finder = DAOStarFinder(threshold=self.threshold, fwhm=fwhm)
    
    def compute(self, image: np.ndarray) -> float:
        stars = self.finder(image)
        if stars is None:
            return 0
        return len(stars)