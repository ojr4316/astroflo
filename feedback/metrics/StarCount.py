from feedback_classifier.metrics.QualityMetric import QualityMetric, Metric
from photutils.detection import DAOStarFinder
import numpy as np
from photutils.background import Background2D, MedianBackground

class StarCount(QualityMetric):
    def __init__(self, threshold: float = 5, fwhm: float = 3.0):
        super().__init__(Metric.STARCOUNT)
        self.threshold = threshold  
        self.fwhm = fwhm
        self.finder = DAOStarFinder(threshold=threshold, fwhm=fwhm)
        
    
    def compute(self, image: np.ndarray) -> float:
        bkg = Background2D(image, box_size=(50, 50), filter_size=(3, 3), bkg_estimator=MedianBackground())
        data_sub = image - bkg.background
        sigma = 5.0
        background_rms = np.median(bkg.background_rms)
        threshold = max(10, background_rms * sigma)
        self.finder = DAOStarFinder(threshold=threshold, fwhm=self.fwhm, exclude_border=True)
        stars = self.finder(data_sub)
        if stars is None:
            return 0
        print(len(stars))
        return len(stars)