from metrics.QualityMetric import Metric
from rules.ClassificationRule import ClassificationRule

class CapOnRule(ClassificationRule):
    def __init__(self, min_stars: int = 7, min_snr: float = 2.0, priority: int = 100):
        super().__init__(priority)
        self.min_stars = min_stars
        self.min_snr = min_snr

    def evaluate(self, metrics: dict) -> bool:
        return metrics.get(Metric.SNR) < self.min_snr